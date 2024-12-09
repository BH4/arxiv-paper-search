import os
import feedparser
import regex
from datetime import datetime
import json
import logging

from summarizer import summarize
import email_sender
import settings


CLEANR = regex.compile('<.*?>')
filename = 'history/'+datetime.today().strftime('%Y-%m-%d')

if os.path.exists(f'{filename}.log'):
    print('Already run today.')
    quit()

logging.basicConfig(filename=f'{filename}.log', encoding='utf-8', level=logging.DEBUG)


def cleanhtml(raw_html):
    cleantext = regex.sub(CLEANR, '', raw_html)
    return cleantext


def todays_feed(sub):
    # ArXiv RSS feed URL
    rss_feed_url = "http://export.arxiv.org/rss/"+sub
    feed = feedparser.parse(rss_feed_url)
    return feed


def author_match(first_last, author):
    if first_last == author:
        return True, 'Full match'

    if author[0] == first_last[0] and '.' == author[1]:
        last = first_last.split()[-1]
        return last in author, 'Abbreviated match'

    return False, None


def author_check(authors):
    matches = []
    reasoning = []
    for a in authors:
        for w in settings.watched_authors:
            match, reason = author_match(w, a)
            if match:
                matches.append(w)
                reasoning.append(reason+' '+w)

    return matches, reasoning


def keyword_to_regex(k):
    words = k.split()
    pattern = r'\b'
    for w in words:
        if len(w) <= 2:
            pattern += '('+w+')'
        elif len(w) <= 5:
            pattern += '('+w+'){e<2}'
        else:
            pattern += '('+w+'){e<3}'
        pattern += r'\s+'
    pattern = pattern[:-3]+r'\b'
    return pattern


def keyword_fuzzy_match(text):
    # Returns a count of matches for each key along with the key/reasoning
    text = text.lower()

    found_groups = []
    matches = []
    for identifier, k_group in settings.watched_keywords:
        k_group_matches = []
        for k in k_group:
            if k in text:
                k_group_matches.append((text.count(k), f'Key: {k}'))
            else:
                pattern = keyword_to_regex(k)
                fuzzy_match = regex.search(pattern, text, flags=regex.IGNORECASE)
                if fuzzy_match is not None:
                    # substitutions, insertions, deletions.
                    actual = fuzzy_match.group(0)
                    fuzzy_type = fuzzy_match.fuzzy_counts
                    count = len(regex.findall(pattern, text, flags=regex.IGNORECASE))

                    k_group_matches.append((count, f'Key: {k} -> {actual}: fuzzy type: {fuzzy_type}'))

        if len(k_group_matches) > 0:
            found_groups.append(identifier)
            matches.append(k_group_matches)

    return found_groups, matches


def get_papers():
    found_papers = []

    total_feed_papers = 0
    for sub in settings.subjects:
        feed = todays_feed(sub)

        # Iterate over each entry in the feed
        for entry in feed.entries:
            total_feed_papers += 1

            title = entry.title
            summary = entry.summary.split('\n')
            number_and_announce_type = summary[0]
            abstract = ' '.join(summary[1:])

            if 'Abstract: ' == abstract[:10]:
                abstract = abstract[10:]

            abstract = abstract.replace('<p>', ' ')
            abstract = abstract.replace('</p>', ' ')
            authors = entry.authors[0]['name'].split(', ')
            authors = [cleanhtml(x).strip() for x in authors]
            link = entry.link

            # Fuzzy search of combined title and abstract
            existing_key_groups, key_matches = keyword_fuzzy_match(title+' '+abstract)

            # Author check
            author_matches, author_match_reasons = author_check(authors)
            importance = settings.paper_importance(existing_key_groups, author_matches)
            if importance > 0:
                if settings.summarize_abstract:
                    abstract = summarize(abstract)
                found_papers.append((importance, title, abstract, authors, link, key_matches, author_match_reasons))

    found_papers = sorted(found_papers, reverse=True, key=lambda t: t[0])
    logging.info(f'Found {len(found_papers)} interesting papers today out of {total_feed_papers}.')
    logging.info(f'Paper importance values: {[x[0] for x in found_papers]}')
    return found_papers


def load_saved_papers(verbose=True):
    """
    Load papers from saved json file. Note that converting to json and loading
    back to python has converted the tuples to lists. This converts them back.
    """
    if not os.path.exists('saved_papers.json'):
        return []

    with open('saved_papers.json', 'r') as f:
        # data = f.read()
        papers = json.load(f)

    # papers = json.loads(data)
    papers = [tuple(x) for x in papers]

    if verbose:
        logging.info(f'Loaded in {len(papers)} papers.')
    return papers


def save_papers(papers):
    """
    Save papers in a json format.

    To ensure we don't lose data we will load whatever the current json file is
    even if it has already been loaded.
    """
    papers.extend(load_saved_papers(verbose=False))
    papers = sorted(papers, reverse=True, key=lambda t: t[0])
    papers = remove_duplicates(papers, verbose=False)

    with open('saved_papers.json', 'w') as f:
        json.dump(papers, f)


def remove_duplicates(papers, verbose=True):
    """
    Sometimes a single paper shows up multiple times, probably from updates to
    the paper being pushed before it is published. This removes those from a
    single email but will not keep track of all papers which have been in
    previous emails. This method is also agnostic to which version is kept.
    """

    links = set()
    unduped = []
    for paper in papers:
        if paper[4] not in links:
            unduped.append(paper)
            links.add(paper[4])

    if verbose:
        logging.info(f'Removed {len(papers)-len(unduped)} duplicates.')
    return unduped


def send_papers(papers):
    """
    Preprocess papers: load older papers, sort by relevance, remove duplicates,
    and save them if necessary.

    First compose the papers into a readable format then send.

    Also write out the email as a html document for reference later.
    """
    papers.extend(load_saved_papers())

    # Sort papers on importance
    papers = sorted(papers, reverse=True, key=lambda t: t[0])

    papers = remove_duplicates(papers)

    if len(papers) == 0:
        logging.info('No papers to save or send.')
        # refresh token even if no papers today
        email_sender.get_credentials()
        return 

    # Check that today is an email day. If not save papers for now.
    if datetime.today().weekday() not in settings.email_days:
        logging.info('Saving papers without email due to day of week settings.')
        save_papers(papers)
        # refresh token every day
        email_sender.get_credentials()
        return

    # Finished prep, compose email.
    logging.info('Sending papers.')
    email_body = ''

    for paper in papers:
        # Main info
        abs_txt = 'Abstract'
        if settings.summarize_abstract:
            abs_txt = 'Summarized Abstract'
        authors = ', '.join(paper[3])
        email_body += f'<b>{paper[1]}</b><br/>{authors}<br/><br/><b>{abs_txt}:</b><br/>{paper[2]}<br/>'

        # Add link
        link = paper[4]
        email_body += f'<a href="{link}">{link}</a><br/><br/>'

        # Add reasoning
        if len(paper[6]) > 0:
            email_body += '<b>Author matches:</b><br/>'
            for a in paper[6]:
                email_body += f'{a}'+', '
            email_body = email_body[:-2]+'<br/>'

        if len(paper[5]) > 0:
            email_body += '<b>Keyword matches:</b><br/>'
            for k_group in paper[5]:
                for count, k in k_group:
                    email_body += f'Count={count}; {k}<br/>'

        # Separate papers
        email_body += '<br/>'

    logging.info('Finished composing email.')
    with open(filename+'.html', 'w') as f:
        f.write(email_body)
    logging.info('Saved draft in file:'+filename+'.html')

    if settings.send_email:
        success, result = email_sender.main(email_body)
        if success:
            logging.info(f"Successfully sent email with id: {result['id']}")

            # Delete the json file since we have now sent out its information.
            os.remove('saved_papers.json')
        else:
            logging.debug(f'Failed to send with error: {result}')


if __name__ == '__main__':
    logging.info('Running')
    papers = get_papers()
    send_papers(papers)
