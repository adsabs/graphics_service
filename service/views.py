from flask import current_app
from flask_restful import Resource
from flask_discoverer import advertise
from graphics import get_graphics
import time

class Graphics(Resource):

    """Return graphics information for a given bibcode"""
    scopes = []
    rate_limit = [1000, 60 * 60 * 24]
    decorators = [advertise('scopes', 'rate_limit')]

    def get(self, bibcode):
        stime = time.time()
        try:
            results = get_graphics(bibcode)
        except Exception, err:
            current_app.logger.error('Graphics exception (%s): %s'%(bibcode, err))
            return {'msg': 'Unable to get results! (%s)' % err}, 500
        if results and results['query'] == 'OK':
            duration = time.time() - stime
            current_app.logger.info('Graphics for %s in %s user seconds'%(bibcode, duration))
            return results
        else:
            current_app.logger.error('Graphics failed (%s): %s'%(bibcode, results.get('error','NA')))
            return {'Error': 'Unable to get results!',
                    'Error Info': results.get('error', 'NA')}, 200
