# Daily arXiv paper search

This project checks today's arXiv rss feed in all your specified subjects for papers which match your specified keywords or authors. Keywords are searched for in the title and abstract and use a fuzzy search so they don't need to match exactly what is used in the paper.

The results are saved in an html file which includes the papers title, authors, a summarized abstract, and information explaining why this paper was selected. This same information can also be sent by email if configured.

## Caveats

The email functionality currently requires setting up your own email sending service, OAuth, ect. but if the project becomes popular this can be streamlined. Create an issue if you would like more detailed instructions on this than those provided in the "email_sender.py" file.


