##### Make your settings file with the name settings.py

###############################################################################
# Email settings
###############################################################################
send_email = False
to_email = 'your_email@provider.com'
from_email = 'your_sendding_email@provider.com'

###############################################################################
# Content settings
###############################################################################
summarize_abstract = False
"""Keywords should be specified as a tuple where the first element is the
"group identifier" which is just a string used in the "paper_meets_requirements"
logic function and the second element should be a list of keywords as strings
which fit that category.
"""
watched_keywords = [('NN', ['neural-network', 'machine learning', 'deepmind']),
                    ('N', ['nucli', 'nucleus']),
                    ('NS', ['neutron star', 'neutron matter', 'nuclear matter'])]
"""
List the full name of authors of interest. The code by default also looks for
first initial with last name.
"""
watched_authors = ['Not Real', 'Aperson Name', 'First Last']

# Arxiv subjects of interest.
subjects = ['nucl-th', 'quant-ph', 'hep-ph', 'astro-ph.HE']


def paper_meets_requirements(found_key_groups, found_authors):
    """
    found_key_groups: List of "group identifiers" specified by the
                      watched_keywords list.
    found_authors: Author full names which are seen in the author list.

    Function supplying the logic for which papers are of interest. 
    This function is run on each paper and the inputs are information found
    about a particular paper. Returns a boolian which if True will prompt the
    code to keep this paper.

    Replace this code with whatever will make a paper interesting to you.
    """
    # Example: if group 'NN' is found and at least one other group
    interesting_keywords = ('NN' in found_key_groups and len(found_key_groups) > 1)
    # Example: If any authors I'm interested in publish I also want to see it.
    interesting_authors = len(found_authors) > 0

    return interesting_keywords or interesting_authors
