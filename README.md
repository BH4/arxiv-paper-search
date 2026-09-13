# Daily arXiv paper search

This project checks today's arXiv rss feed in all your specified subjects for papers which match your specified keywords or authors. Keywords are searched for in the title and abstract and use a fuzzy search so they don't need to match exactly what is used in the paper.

The results are saved in an html file which includes the papers title, authors, a summarized abstract, and information explaining why this paper was selected. This same information can also be sent by email if configured.

## Setup

Requirements can be installed through pip with
`pip install -r requirements.txt`

The "settings_example.py" file should be renamed "settings.py" and changed to your preferences. Importantly, your interests should be catagorized by the "watched_keywords" variable. Each tuple, starting with an identifier string and ending with a list of strings specifies a broad category of interest (i.e. neural networks) which will be matched if any of the strings in its list appear in the title or abstract. Overlaps between subjects can be selected in the `paper_importance` function.

The `paper_importance()` function is called for every paper with a list of the keyword groups that were found (as a list of the identifier strings you specify) and the list of authors which match those you specify. From this function you return an integer value rating the paper. If 0, this paper is ignored. The final html file/email will be sorted with larger importance values at the top.

Running main.py can be automated through any task scheduler program (cron, task scheduler, ect.).

## Email Setup

The email functionality requires setting up your own email sending service, OAuth, ect. This is done by following the settings here https://developers.google.com/gmail/api/quickstart/python and including the credentials.json file created in this process inside the main directory of this project.


