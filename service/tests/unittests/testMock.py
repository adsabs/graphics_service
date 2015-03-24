import sys, os
PROJECT_HOME = os.path.abspath(os.path.join(os.path.dirname(__file__),'../../'))
sys.path.append(PROJECT_HOME)
from flask.ext.testing import TestCase
from flask import url_for, Flask
from utils.database import db
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.dialects import postgresql
import unittest
import requests
import app
import mock

from utils.database import GraphicsModel
from datetime import datetime

def get_testdata():
    global figures
    figures = [{"images": [{"image_id": "fg1", "format": "gif", "thumbnail": "fg1_thumb_url", "highres": "fg1_highres_url"}], "figure_caption": "Figure 1", "figure_label": "Figure 1", "figure_id": "fg1"}]
    g = GraphicsModel(
            bibcode = '9999BBBBBVVVVQPPPPI',
            doi = 'DOI',
            source = 'TEST',
            eprint = False,
            figures = figures,
            modtime = datetime.now()
        )
    return g

class TestExpectedResults(TestCase):
    def create_app(self):
        '''Create the wsgi application'''
        app_ = app.create_app()
        db.session = mock.Mock()
        one = db.session.query.return_value.filter.return_value.one
        one.return_value = get_testdata()
        return app_

    def test_data_model(self):
        '''Check that data model for graphics is what we expect'''
        ic = Column(Integer)
        sc = Column(String)
        bc = Column(Boolean)
        jc = Column(postgresql.JSON)
        dc = Column(DateTime)
        cols_expect = map(type, [ic.type, sc.type, sc.type, sc.type, bc.type, jc.type, dc.type])
        self.assertEqual([type(c.type) for c in GraphicsModel.__table__.columns], cols_expect)

    def test_query_1(self):
        '''Check that session mock behaves the way we set it up'''
        expected_attribs = ['modtime', 'bibcode', 'source', '_sa_instance_state', 'eprint', 'figures', 'id', 'doi']
        resp = db.session.query(GraphicsModel).filter(GraphicsModel.bibcode=='9999BBBBBVVVVQPPPPI').one()
        self.assertEqual(resp.__dict__.keys().sort(), expected_attribs.sort())

    def test_query(self):
        '''Query endpoint with bibcode from stub data should return expected results'''
        url = url_for('graphics.graphics',bibcode='9999BBBBBVVVVQPPPPI')
        r = self.client.get(url)
        self.assertTrue(r.status_code == 200)
        self.assertTrue(r.json.get('figures') == figures)
        self.assertTrue(r.json.get('bibcode') == '9999BBBBBVVVVQPPPPI')
        self.assertTrue(r.json.get('pick')['figure_label'] == 'Figure 1')

class TestDatabaseError(TestCase):
    def create_app(self):
        '''Create the wsgi application'''
        app_ = app.create_app()
        db.session = mock.Mock()
        one = db.session.query.return_value.filter.return_value.one
        one.return_value = Exception()
        return app_
    def test_query(self):
       ''''An exception is returned representing the absence of a database connection'''
       url = url_for('graphics.graphics',bibcode='9999BBBBBVVVVQPPPPI')
       r = self.client.get(url)
       self.assertTrue(r.status_code == 500)

class TestNoDataReturned(TestCase):
    def create_app(self):
        '''Create the wsgi application'''
        app_ = app.create_app()
        db.session = mock.Mock()
        one = db.session.query.return_value.filter.return_value.one
        one.return_value = Exception("No row found")
        return app_
    def test_query(self):
       ''''An exception is returned when no row is found in database'''
       url = url_for('graphics.graphics',bibcode='9999BBBBBVVVVQPPPPI')
       r = self.client.get(url)
       self.assertTrue(r.status_code == 404)


if __name__ == '__main__':
    unittest.main()
