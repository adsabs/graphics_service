import sys
import ptree
from flask import Flask
from flask import request
from flask import Blueprint
from flask.ext.restful import Api, Resource
from config import config
from graphics_utils import get_graphics

app_blueprint = Blueprint('api', __name__)
api = Api(app_blueprint)

class Graphics(Resource):
    """"Return graphics information for a given bibcode"""
    scope = 'oauth:graphics:read'
    def get(self, bibcode):
       try:
           results = get_graphics(bibcode)
       except Exception, err:
           return {'msg': 'Unable to get results! (%s)' % err}, 500
       return results

class DisplayGraphics(Resource):
    """Return image data for a given figure"""
    scope = 'oauth:displaygraphics:read'
    def get(self,bibcode,figure_id,image_format):
        format2ext = {'tb':'gif','lr':'jpg','hr':'png'}
        image_ext = format2ext.get(image_format,'png')
        image_dir = config.IMAGE_PATH + ptree.id2ptree(bibcode)
        image = "%s%s_%s_%s.%s" % (image_dir,bibcode,figure_id,image_format,image_ext)
        try:
            image_data = open(image, "rb").read()
        except Exception, e:
            sys.stderr.write('Unable to get image %s (format: %s) for bibcode : %s! (%s)' % (figure_id,image_format,bibcode,e))
            return ('', 204)
        header = {'Content-type': 'image/%s'%image_ext}
        return image_data, 200, header

class Resources(Resource):
    """Overview of available resources"""
    scope = 'oauth:resources:read'
    def get(self):
        func_list = {}
        for rule in app.url_map.iter_rules():
            func_list[rule.rule] = {'methods':app.view_functions[rule.endpoint].methods,
                                    'scope': app.view_functions[rule.endpoint].view_class.scope,
                                    'description': app.view_functions[rule.endpoint].view_class.__doc__,
                                       }
        return func_list

##
## Actually setup the Api resource routing here
##
api.add_resource(Graphics, '/graphics/<string:bibcode>')
api.add_resource(DisplayGraphics,'/<string:bibcode>/<string:figure_id>/<string:image_format>')
api.add_resource(Resources, '/resources')

if __name__ == '__main__':
    app = Flask(__name__, static_folder=None)
    app.register_blueprint(app_blueprint)
    app.run(debug=True)
