SECRET_KEY = 'this should be changed'
SQLALCHEMY_DATABASE_URI = ''
INCLUDE_ARXIV = False
SQLALCHEMY_BINDS = {}
#This section configures this application to act as a client, for example to query solr via adsws
CLIENT = {
  'TOKEN': 'we will provide an api key token for this application'
}
# Define the autodiscovery endpoint
DISCOVERER_PUBLISH_ENDPOINT = '/resources'
# Advertise its own route within DISCOVERER_PUBLISH_ENDPOINT
DISCOVERER_SELF_PUBLISH = False
