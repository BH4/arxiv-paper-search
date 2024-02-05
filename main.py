import os
import feedparser
import regex
from datetime import datetime
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

    if '.' == author[1] and author[0] == first_last[0]:
        last = first_last.split()[1]
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

    for sub in settings.subjects:
        feed = todays_feed(sub)

        # Iterate over each entry in the feed
        for entry in feed.entries:
            title = entry.title
            abstract = entry.summary.replace('\n', ' ')
            abstract = abstract.replace('<p>', ' ')
            abstract = abstract.replace('</p>', ' ')
            authors = entry.authors[0]['name'].split('\n')
            authors = [cleanhtml(x).strip() for x in authors]
            link = entry.link

            # Fuzzy search of combined title and abstract
            existing_key_groups, key_matches = keyword_fuzzy_match(title+' '+abstract)

            # Author check
            author_matches, author_match_reasons = author_check(authors)
            if settings.paper_meets_requirements(existing_key_groups, author_matches):
                if settings.summarize_abstract:
                    abstract = summarize(abstract)
                found_papers.append((title, abstract, authors, link, key_matches, author_match_reasons))

    logging.info(f'Found {len(found_papers)} interesting papers.')

    # calculate paper importance and sort
    # ....

    return found_papers


def send_papers(papers):
    """
    First compose the papers into a readable format then send.

    Also write out the email as a txt document for reference later.
    """
    email_body = ''

    for paper in papers:
        # Main info
        abs_txt = 'Abstract'
        if settings.summarize_abstract:
            abs_txt = 'Summarized Abstract'
        authors = ', '.join(paper[2])
        email_body += f'<b>{paper[0]}</b><br/>{authors}<br/><br/><b>{abs_txt}:</b><br/>{paper[1]}<br/>'

        # Add link
        link = paper[3]
        email_body += f'<a href="{link}">{link}</a><br/><br/>'

        # Add reasoning
        if len(paper[5]) > 0:
            email_body += '<b>Author matches:</b><br/>'
            for a in paper[5]:
                email_body += f'{a}'+', '
            email_body = email_body[:-2]+'<br/>'

        if len(paper[4]) > 0:
            email_body += '<b>Keyword matches:</b><br/>'
            for k_group in paper[4]:
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
        if success is None:
            logging.debug('No idea what happened.')
        if success:
            logging.info(f"Successfully sent email with id: {result['id']}")
        else:
            logging.debug(f'Failed to send with error: {result}')


if __name__ == '__main__':
    logging.info('Running')
    papers = get_papers()
    if len(papers) > 0:
        logging.info('Sending papers.')
        send_papers(papers)  # only saves if not emailing
    elif settings.send_email:
        # refresh token
        email_sender.get_credentials()
