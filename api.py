import sys
import ptree
from flask import Flask
from flask import request
from flask import jsonify
from flask.ext.restful import abort, Api, Resource
from config import config
from graphics_utils import get_graphics

app = Flask(__name__)
api = Api(app)

class Graphics(Resource):
    def get(self, bibcode):
       try:
           results = get_graphics(bibcode)
       except Exception, err:
            sys.stderr.write('Unable to get results! (%s)' % err)
            abort(400)
       return jsonify(results)

class DisplayGraphics(Resource):
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
    def get(self):
      return config.RESOURCES
##
## Actually setup the Api resource routing here
##
api.add_resource(Graphics, '/graphics/<string:bibcode>')
api.add_resource(DisplayGraphics,'/<string:bibcode>/<string:figure_id>/<string:image_format>')
api.add_resource(Resources, '/resources')

if __name__ == '__main__':
    app.run(debug=True)
