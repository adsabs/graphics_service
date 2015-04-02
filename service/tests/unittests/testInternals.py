import sys, os
PROJECT_HOME = os.path.abspath(os.path.join(os.path.dirname(__file__),'../../'))
sys.path.append(PROJECT_HOME)
from flask.ext.testing import TestCase
from flask import request
from flask import url_for, Flask
import unittest
import requests
import time
import app

class TestConfig(TestCase):
  '''Check if config has necessary entries'''
  def create_app(self):
    '''Create the wsgi application'''
    app_ = app.create_app()
    return app_

  def test_config_values(self):
    '''Check if all required config variables are there'''
    required = ["GAPHICS_INCLUDE_ARXIV","SQLALCHEMY_BINDS","GRAPHICS_API_TOKEN","DISCOVERER_PUBLISH_ENDPOINT","DISCOVERER_SELF_PUBLISH"]

    missing = [x for x in required if x not in self.app.config.keys()]
    self.assertTrue(len(missing)==0)
    # Check if API has an actual value
    self.assertTrue(self.app.config.get('GRAPHICS_API_TOKEN',None) != None)

if __name__ == '__main__':
  unittest.main()
