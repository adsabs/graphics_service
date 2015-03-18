from flask import current_app, Blueprint, request
from flask.ext.restful import Resource
from flask.ext.discoverer import advertise
import time
import ptree
import inspect
import sys

from utils.graphics import get_graphics

blueprint = Blueprint(
      'graphics',
      __name__,
      static_folder=None,
)

class Graphics(Resource):
    """Return graphics information for a given bibcode"""
    scopes = []
    rate_limit = [1000,60*60*24]
    decorators = [advertise('scopes','rate_limit')]
    def get(self, bibcode):
       try:
           results = get_graphics(bibcode)
       except Exception, err:
           return {'msg': 'Unable to get results! (%s)' % err}, 500
       if results and results['query'] == 'OK':
           return results
       else:
           return {'msg': 'Unable to get results! (%s)' % results.get('error','NA')}, 404

class DisplayGraphics(Resource):
    """Return image data for a given figure"""
    scopes = []
    rate_limit = [1000,60*60*24]
    decorators = [advertise('scopes','rate_limit')]
    def get(self,bibcode,figure_id,image_format):
        format2ext = {'tb':'gif','lr':'jpg','hr':'png'}
        image_ext = format2ext.get(image_format,'png')
        image_dir = current_app.config['IMAGE_PATH'] + ptree.id2ptree(bibcode)
        image = "%s%s_%s_%s.%s" % (image_dir,bibcode,figure_id,image_format,image_ext)
        try:
            image_data = open(image, "rb").read()
        except Exception, e:
            sys.stderr.write('Unable to get image %s (format: %s) for bibcode : %s! (%s)' % (figure_id,image_format,bibcode,e))
            return ('', 204)
        header = {'Content-type': 'image/%s'%image_ext}
        return image_data, 200, header
