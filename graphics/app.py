import os
from flask import Flask, g
from views import blueprint, Resources, UnixTime, PrintArg, ExampleApiUsage, Graphics, DisplayGraphics
from flask.ext.restful import Api
from client import Client

def create_app():
  api = Api(blueprint)
  api.add_resource(Resources, '/resources')
  api.add_resource(UnixTime, '/time')
  api.add_resource(PrintArg,'/print/<string:arg>')
  api.add_resource(ExampleApiUsage,'/search')
  api.add_resource(Graphics, '/graphics/<string:bibcode>')
  api.add_resource(DisplayGraphics,'/<string:bibcode>/<string:figure_id>/<string:image_format>')

  app = Flask(__name__, static_folder=None)
  app.url_map.strict_slashes = False
  app.config.from_object('graphics.config')
  try:
    app.config.from_object('graphics.local_config')
  except ImportError:
    pass
  app.register_blueprint(blueprint)
  app.client = Client(app.config['CLIENT'])
  return app
