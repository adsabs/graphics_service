from flask import current_app
from flask.ext.restful import Resource
from flask.ext.discoverer import advertise
from graphics import get_graphics


class Graphics(Resource):

    """Return graphics information for a given bibcode"""
    scopes = []
    rate_limit = [1000, 60 * 60 * 24]
    decorators = [advertise('scopes', 'rate_limit')]

    def get(self, bibcode):
        try:
            results = get_graphics(bibcode)
        except Exception, err:
            return {'msg': 'Unable to get results! (%s)' % err}, 500
        if results and results['query'] == 'OK':
            return results
        else:
            return {'Error': 'Unable to get results!',
                    'Error Info': results.get('error', 'NA')}, 200
