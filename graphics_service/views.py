from __future__ import absolute_import
from flask import current_app
from flask_restful import Resource
from flask_discoverer import advertise
from .graphics import get_graphics
import time

class Graphics(Resource):

    """Return graphics information for a given bibcode"""
    scopes = []
    rate_limit = [1000, 60 * 60 * 24]
    decorators = [advertise('scopes', 'rate_limit')]

    def get(self, bibcode):
        stime = time.time()
        results = get_graphics(bibcode)
        duration = time.time() - stime
        current_app.logger.info('Graphics for %s in %s user seconds'%(bibcode, duration))
        return results, 200
