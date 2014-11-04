from flask import current_app, Blueprint, request
from flask.ext.restful import Resource
import time
import ptree

from graphics_utils import get_graphics

blueprint = Blueprint(
      'graphics',
      __name__,
      static_folder=None,
)

class Graphics(Resource):
    """"Return graphics information for a given bibcode"""
    scopes = 'oauth:graphics:read'
    def get(self, bibcode):
       try:
           results = get_graphics(bibcode)
       except Exception, err:
           return {'msg': 'Unable to get results! (%s)' % err}, 500
       return results

class DisplayGraphics(Resource):
    """Return image data for a given figure"""
    scopes = 'oauth:displaygraphics:read'
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

class Resources(Resource):
  '''Overview of available resources'''
  scopes = ['oauth:sample_application:read','oauth_sample_application:logged_in']
  def get(self):
    func_list = {}
    for rule in current_app.url_map.iter_rules():
      func_list[rule.rule] = {'methods':current_app.view_functions[rule.endpoint].methods,
                              'scopes': current_app.view_functions[rule.endpoint].view_class.scopes,
                              'description': current_app.view_functions[rule.endpoint].view_class.__doc__,
                              }
    return func_list, 200

class UnixTime(Resource):
  '''Returns the unix timestamp of the server'''
  scopes = ['oauth:sample_application:read','oauth_sample_application:logged_in']
  def get(self):
    return {'now': time.time()}, 200
