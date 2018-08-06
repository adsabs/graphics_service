LOG_STDOUT = True
GRAPHICS_SECRET_KEY = 'this should be changed'
# External graphics sources
GRAPHICS_EXTSOURCES = ['IOP', 'Elsevier', 'EDP']
# Some info for the external site
GRAPHICS_HEADER = {
                  'EDP':'Every image links to the article on <a href="http://www.aanda.org/" target="_new">Astronomy &amp; Astrophysics</a>',
                  'IOP':'Every image links to the <a href="http://www.astroexplorer.org/" target="_new">AAS "Astronomy Image Explorer"</a> for more detail.',
                  'IOPscience':'Every image links to the article on <a href="http://iopscience.iop.org/" target="_new">IOPscience</a>',
                  'Elsevier':'Every image links to the article on <a href="http://www.sciencedirect.com" target="_new">ScienceDirect</a>'
                  }
#
GRAPHICS_INCLUDE_ARXIV = True
# Proper handling of database connections
SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://user:pwd@localhost:5432/graphics'
SQLALCHEMY_ECHO = False
SQLALCHEMY_COMMIT_ON_TEARDOWN = True
# Define the autodiscovery endpoint
DISCOVERER_PUBLISH_ENDPOINT = '/resources'
# Advertise its own route within DISCOVERER_PUBLISH_ENDPOINT
DISCOVERER_SELF_PUBLISH = False
