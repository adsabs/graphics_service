import sys
import os
from flask_testing import TestCase
import flask_sqlalchemy
from graphics_service.models import GraphicsModel
from graphics_service.models import AlchemyEncoder
from graphics_service.models import Base
import unittest
import time
from graphics_service import app
import simplejson as json
import mock
from datetime import datetime

def get_testdata(figures = []):
    g = GraphicsModel(
        bibcode='9999BBBBBVVVVQPPPPI',
        doi='DOI',
        source='TEST',
        eprint=False,
        figures=[],
        modtime=datetime.now()
    )
    return g

class TestUtils(TestCase):

    '''Check if config has necessary entries'''

    def create_app(self):
        '''Create the wsgi application'''
        app_ = app.create_app()
        return app_

    def test_config_values(self):
        '''Check if all required config variables are there'''
        required = ["GRAPHICS_INCLUDE_ARXIV", "SQLALCHEMY_DATABASE_URI",
                    "DISCOVERER_PUBLISH_ENDPOINT", "DISCOVERER_SELF_PUBLISH"]

        missing = [x for x in required if x not in self.app.config.keys()]
        self.assertTrue(len(missing) == 0)

    def test_json_encoder(self):
        '''Check if SQLAlchemy model gets translated into JSON properly'''

        g = GraphicsModel(
                bibcode='bibcode',
                doi='DOI',
                source='TEST',
                eprint=False,
                figures=[],
                modtime=datetime.now()
            )
        results = json.loads(json.dumps(g, cls=AlchemyEncoder))
        expected = {'modtime': None, 'bibcode': 'bibcode', 'source': 'TEST', 'doi': 'DOI', 'figures': [], 'eprint': False, 'id': None} 
        self.assertTrue(results==expected)

class TestLocalConfig(TestCase):

    '''Check if config has necessary entries'''

    def create_app(self):
        '''Create the wsgi application'''
        app_ = app.create_app(**{
            'FOO': ['bar', {}],
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///',
               })
        return app_

    def test_config_values(self):
        '''Check if we see local config'''
        self.assertEqual(self.app.config['FOO'], ['bar', {}])

class TestDatabaseQuery(TestCase):
    def create_app(self):
        '''Create the wsgi application'''
        g = GraphicsModel(
                bibcode='bibcode',
                doi='DOI',
                source='TEST',
                eprint=False,
                figures=[],
                modtime=datetime.now()
            )

        app_ = app.create_app()
        app_.db.session = mock.MagicMock()

        return app_

    def test_query(self):
        from graphics_service.models import execute_SQL_query

        res = execute_SQL_query('a')


if __name__ == '__main__':
    unittest.main(verbosity=2)
