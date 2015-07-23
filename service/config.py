GRAPHICS_SECRET_KEY = 'this should be changed'
GRAPHICS_INCLUDE_ARXIV = False
SQLALCHEMY_BINDS = {}
GRAPHICS_ENABLE_UPDATES = False
# Define sets for which to obtain graphics data for graphics database
# The key defines the set and the values are journals (or categories, in the
# case of arXiv)
GRAPHICS_PUBSETS = {
                   'IOP':['ApJ','ApJL','ApJS','AJ'],
                   'arXiv': ['arXiv', 'acc-phys', 'adap-org', 'alg-geom',
                             'ao-sci', 'astro-ph', 'atom-ph', 'bayes-an',
                             'chao-dyn', 'chem-ph', 'cmp-lg', 'comp-gas',
                             'cond-mat', 'cs', 'dg-ga', 'funct-an', 'gr-qc',
                             'hep-ex', 'hep-lat', 'hep-ph', 'hep-th', 'math',
                             'math-ph', 'mtrl-th', 'nlin', 'nucl-ex', 'nucl-th',
                             'patt-sol', 'physics', 'plasm-ph', 'q-alg', 'q-bio',
                             'quant-ph', 'solv-int', 'supr-con']
                  }
# Define the mapping to help retrieve full text files for a given identifier
GRAPHICS_FULLTEXT_MAPS = {
    'IOP':'/path/to/IOP.map',
    'arXiv':'/path/to/arXiv.map'
}
# Define a file with backdata, if available
GRAPHICS_BACK_DATA_FILE = {
}
# These are the values to be stored as "source" in the graphics database
GRAPHICS_SOURCE_NAMES = {
    'IOP': 'IOP',
    'arXiv': 'arXiv',
}
# Work directory to store temporary data (e.g. for unpacking TAR files)
GRAPHICS_TMP_DIR = ''
# Base directory of where extracted images will be stored
GRAPHICS_IMAGE_DIR = ''
# Base URL for serving images
GRAPHICS_BASE_URL = ''
# Vertical size for thumbnails
GRAPHICS_THMB_SIZE = '100'
# How do we query Solr
GRAPHICS_SOLR_PATH = 'https://api.adsabs.harvard.edu/v1/search/query'
# This section configures this application to act as a client, for example
# to query solr via adsws
GRAPHICS_API_TOKEN = 'we will provide an api key token for this application'
# Define the autodiscovery endpoint
DISCOVERER_PUBLISH_ENDPOINT = '/resources'
# Advertise its own route within DISCOVERER_PUBLISH_ENDPOINT
DISCOVERER_SELF_PUBLISH = False
