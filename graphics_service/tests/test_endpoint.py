from __future__ import print_function
from builtins import map
import sys
import os
from flask_testing import TestCase
from flask import url_for
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import DateTime
from sqlalchemy import Boolean
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm.exc import NoResultFound
from graphics_service import app
from graphics_service.models import GraphicsModel
from graphics_service.models import AlchemyEncoder
import simplejson as json
import mock
from datetime import datetime

def get_testdata(figures = [], source='TEST'):
    g = GraphicsModel(
        bibcode='9999BBBBBVVVVQPPPPI',
        doi='DOI',
        source=source,
        eprint=False,
        figures=figures,
        modtime=datetime.now()
    )
    results = json.loads(json.dumps(g, cls=AlchemyEncoder))
    return results

class TestExpectedResults(TestCase):

    figure_data = [{"images": [{"image_id": "fg1", "format": "gif",
                            "thumbnail": "fg1_thumb_url", "highres":
                            "fg1_highres_url"}],
                "figure_caption": "Figure 1",
                "figure_label": "Figure 1",
                "figure_id": "fg1"}]

    figure_data_no_thumb = [{"images": [{"image_id": "fg1", "format": "gif"}],
                "figure_caption": "Figure 1",
                "figure_label": "Figure 1",
                "figure_id": "fg1"}]

    def create_app(self):
        '''Create the wsgi application'''
        app_ = app.create_app()
        return app_

    def test_data_model(self):
        '''Check that data model for graphics is what we expect'''
        ic = Column(Integer)
        sc = Column(String)
        bc = Column(Boolean)
        jc = Column(postgresql.JSON)
        tc = Column(postgresql.ARRAY(String))
        uc = Column(String)
        dc = Column(DateTime)
        cols_expect = list(map(
            type, [ic.type, sc.type, sc.type, sc.type, bc.type,
                   jc.type, tc.type, uc.type, dc.type]))
        self.assertEqual([type(c.type)
                          for c in GraphicsModel.__table__.columns],
                         cols_expect)

    @mock.patch('graphics_service.models.execute_SQL_query', return_value=get_testdata(figures=figure_data))
    def test_query(self, mock_execute_SQL_query):
        '''Query endpoint with bibcode from stub data should
           return expected results'''
        url = url_for('graphics', bibcode='9999BBBBBVVVVQPPPPI')
        r = self.client.get(url)
        self.assertTrue(r.status_code == 200)
        self.assertTrue(r.json.get('figures') == self.figure_data)
        self.assertTrue(r.json.get('bibcode') == '9999BBBBBVVVVQPPPPI')
        self.assertTrue(r.json.get('pick')['figure_label'] == 'Figure 1')

    @mock.patch('graphics_service.models.execute_SQL_query', return_value=get_testdata(figures=figure_data_no_thumb, source='IOP'))
    def test_query_no_thumbnail(self, mock_execute_SQL_query):
        '''Query endpoint with bibcode from stub data should
           return expected results'''
        url = url_for('graphics', bibcode='9999ApJ..VVVVQPPPPI')
        r = self.client.get(url)
        self.assertTrue(r.status_code == 200)
        expected = {u'Error Info': u'Failed to get thumbnail for display image for 9999ApJ..VVVVQPPPPI', u'Error': u'Unable to get results!'}
        self.assertTrue(r.json == expected)

    @mock.patch('graphics_service.models.execute_SQL_query', return_value=get_testdata(figures=figure_data_no_thumb, source='ARXIV'))
    def test_query_no_thumbnail_2(self, mock_execute_SQL_query):
        '''Query endpoint with bibcode from stub data should
           return expected results'''
        url = url_for('graphics', bibcode='9999ApJ..VVVVQPPPPI')
        r = self.client.get(url)
        self.assertTrue(r.status_code == 200)
        expected = {u'Error Info': u'Failed to get thumbnail for display image for 9999ApJ..VVVVQPPPPI', u'Error': u'Unable to get results!'}
        self.assertTrue(r.json == expected)

    @mock.patch('graphics_service.models.execute_SQL_query')
    def test_query_exception(self, mock_execute_SQL_query):
        ''''An exception is returned representing the absence of
            a database connection'''
        mock_execute_SQL_query.side_effect = Exception('something went wrong')
        url = url_for('graphics', bibcode='foo')
        r = self.client.get(url)
        self.assertTrue(r.status_code == 200)
        expected = {u'Error Info': u'Graphics query failed for foo: something went wrong', u'Error': u'Unable to get results!'}
        self.assertTrue(r.json == expected)

    @mock.patch('graphics_service.models.execute_SQL_query')
    def test_query_no_record(self, mock_execute_SQL_query):
        ''''An exception is returned representing the absence of
            a record in the database'''
        mock_execute_SQL_query.side_effect = NoResultFound
        url = url_for('graphics', bibcode='foo')
        r = self.client.get(url)
        self.assertTrue(r.status_code == 200)
        expected = {u'Error Info': u'No database entry found for foo', u'Error': u'Unable to get results!'}
        print(r.json)
        self.assertTrue(r.json == expected)

    @mock.patch('graphics_service.models.execute_SQL_query', return_value={'Error': 'error', 'Error Info': 'info'})
    def test_query_error(self, mock_execute_SQL_query):
        ''''An exception is returned representing the absence of
            a database connection'''
        url = url_for('graphics', bibcode='foo')
        r = self.client.get(url)
        self.assertTrue(r.status_code == 200)
        expected = {u'Error Info': u'info', u'Error': u'error'}
        self.assertTrue(r.json == expected)

    @mock.patch('graphics_service.models.execute_SQL_query', return_value=get_testdata())
    def test_query_no_data(self, mock_execute_SQL_query):
        '''Query endpoint with bibcode from stub data should
           return expected results'''
        url = url_for('graphics', bibcode='foo')
        r = self.client.get(url)
        self.assertTrue(r.status_code == 200)
        expected = {u'Error Info': u'No figure data for foo', u'Error': u'Unable to get results!'}
        self.assertTrue(r.json == expected)

    @mock.patch('graphics_service.models.execute_SQL_query', return_value=get_testdata(figures=figure_data, source='IOP'))
    def test_query_IOPScience(self, mock_execute_SQL_query):
        '''Query endpoint with bibcode from stub data should
           return expected results'''
        header = self.app.config.get('GRAPHICS_HEADER').get('IOPscience')
        url = url_for('graphics', bibcode='9999BBBBBVVVVQPPPPI')
        r = self.client.get(url)
        self.assertTrue(r.status_code == 200)
        self.assertEqual(r.json['header'], header)

    @mock.patch('graphics_service.models.execute_SQL_query', return_value=get_testdata(figures=figure_data, source='IOP'))
    def test_query_IOP(self, mock_execute_SQL_query):
        '''Query endpoint with bibcode from stub data should
           return expected results'''
        header = self.app.config.get('GRAPHICS_HEADER').get('IOP')
        url = url_for('graphics', bibcode='9999ApJ..VVVVQPPPPI')
        r = self.client.get(url)
        self.assertTrue(r.status_code == 200)
        self.assertEqual(r.json['header'], header)

    @mock.patch('graphics_service.models.execute_SQL_query', return_value=get_testdata(figures=figure_data, source='EDP'))
    def test_query_EDP(self, mock_execute_SQL_query):
        '''Query endpoint with bibcode from stub data should
           return expected results'''
        header = self.app.config.get('GRAPHICS_HEADER').get('EDP')
        url = url_for('graphics', bibcode='9999BBBBBVVVVQPPPPI')
        r = self.client.get(url)
        self.assertTrue(r.status_code == 200)
        self.assertEqual(r.json['header'], header)

    @mock.patch('graphics_service.models.execute_SQL_query', return_value=get_testdata(figures=figure_data, source='Elsevier'))
    def test_query_Elsevier(self, mock_execute_SQL_query):
        '''Query endpoint with bibcode from stub data should
           return expected results'''
        header = self.app.config.get('GRAPHICS_HEADER').get('Elsevier')
        url = url_for('graphics', bibcode='9999BBBBBVVVVQPPPPI')
        r = self.client.get(url)
        self.assertTrue(r.status_code == 200)
        self.assertEqual(r.json['header'], header)

    @mock.patch('graphics_service.models.execute_SQL_query', return_value=get_testdata(figures=figure_data, source='ARXIV'))
    def test_query_arXiv(self, mock_execute_SQL_query):
        '''Query endpoint with bibcode from stub data should
           return expected results'''
        url = url_for('graphics', bibcode='9999BBBBBVVVVQPPPPI')
        r = self.client.get(url)
        header = 'Images extracted from the arXiv e-print'
        self.assertTrue(r.status_code == 200)
        self.assertEqual(r.json['header'], header)

    @mock.patch('graphics_service.models.execute_SQL_query', return_value=get_testdata(figures=figure_data, source='FOO'))
    def test_query_unknown_source(self, mock_execute_SQL_query):
        '''Query endpoint with bibcode from stub data should
           return expected results'''
        url = url_for('graphics', bibcode='9999BBBBBVVVVQPPPPI')
        r = self.client.get(url)
        self.assertTrue(r.status_code == 200)
        expected = {u'Error Info': u'Unknown data source FOO', u'Error': u'Unable to get results!'}
        self.assertEqual(r.json, expected)

if __name__ == '__main__':
    unittest.main(verbosity=2)
