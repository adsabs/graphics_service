import sys
import os
import shutil
PROJECT_HOME = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(PROJECT_HOME)
from flask.ext.testing import TestCase
from flask import request
from flask import url_for, Flask
from models import db, GraphicsModel
import unittest
import requests
import time
import app
import mock
import json

def get_testdata():
    dfile = "%s/tests/stubdata/IOPstubdata.json" % PROJECT_HOME
    with open(dfile) as data_file:
        data = json.load(data_file)
    g = GraphicsModel(
        bibcode=data['bibcode'],
        doi=data['doi'],
        source=data['source'],
        eprint=data['eprint'],
        figures=data['figures'],
        modtime=data['modtime']
    )
    return g
 
@unittest.skip("skip update testing (IOP)")
class TestIOP(TestCase):

    '''Check IOP processing'''

    def create_app(self):
        '''Create the wsgi application'''
        _app = app.create_app()
        _app.config['GRAPHICS_TMP_DIR'] = "%s/tests/stubdata" % PROJECT_HOME
        db.session = mock.Mock()
        first = db.session.query.return_value.filter.return_value.first
        first.return_value = get_testdata()
        count = db.session.query.count
        count.return_value = 1
        return _app

    def test_config_values(self):
        '''Check if all necessary configs are there and valid'''
        # Only test this if we enabled graphics updates
        if not self.app.config.get('GRAPHICS_ENABLE_UPDATES', False):
            return True
        self.assertTrue(self.app.config.get('GRAPHICS_FULLTEXT_MAPS'))
        self.assertTrue(self.app.config.get('GRAPHICS_FULLTEXT_MAPS').get('IOP'))
        self.assertTrue(self.app.config.get('GRAPHICS_FULLTEXT_MAPS').get('arXiv'))
        self.assertTrue(self.app.config.get('GRAPHICS_BACK_DATA_FILE'))
        self.assertTrue(self.app.config.get('GRAPHICS_BACK_DATA_FILE').get('IOP'))
        self.assertTrue(self.app.config.get('GRAPHICS_SOURCE_NAMES'))
        self.assertTrue(self.app.config.get('GRAPHICS_SOURCE_NAMES').get('IOP'))
        self.assertTrue(self.app.config.get('GRAPHICS_SOURCE_NAMES').get('arXiv'))

    def test_sources(self):
        '''Check that configured sources actually exist'''
        # Only test this if we enabled graphics updates
        if not self.app.config.get('GRAPHICS_ENABLE_UPDATES', False):
            return True
        # The location of IOP fulltext files (stored in file)
        map = self.app.config.get('GRAPHICS_FULLTEXT_MAPS').get('IOP')
        self.assertTrue(os.path.exists(map))
        self.assertTrue(os.path.isfile(map))
        # The location of arXiv fulltext files (base directory)
        map = self.app.config.get('GRAPHICS_FULLTEXT_MAPS').get('arXiv')
        self.assertTrue(os.path.exists(map))
        self.assertTrue(os.path.isdir(map))
        # Graphics back data (only for IOP)
        map = self.app.config.get('GRAPHICS_BACK_DATA_FILE').get('IOP')
        self.assertTrue(os.path.exists(map))
        self.assertTrue(os.path.isfile(map))

    def test_IOP_update(self):
        '''Check update for an IOP publication'''
        from utils import process_IOP_graphics
        if not self.app.config.get('GRAPHICS_ENABLE_UPDATES', False):
            return True
        identifiers = [{'bibcode':'2013ApJ...778L..42P', 'arxid':'arXiv:1311.1201'}]
        map_file = "%s/tests/stubdata/IOP_ft.map" % PROJECT_HOME
        ft_file  = "%s/tests/stubdata/stubdata.xml" % PROJECT_HOME
        # Create map file for full text
        open(map_file, "w").write("2013ApJ...778L..42P\t%s\tIOP" % ft_file)
        # Put this map file in config 
        self.app.config['GRAPHICS_FULLTEXT_MAPS']['IOP'] = map_file
        # First we don't force an update
        # The record is already there (by design), so nothing should happen
        res = process_IOP_graphics(identifiers, False, dryrun=True)
        # Without forcing the update, None should get returned
        self.assertEqual(res, None)
        # Now force an update
        res = process_IOP_graphics(identifiers, True, dryrun=True)
        # The result should now contain a list of figures,
        # of which there are 3
        self.assertEqual(len(res), 3)
        expected_figures = ['Figure 1.', 'Figure 2.', 'Figure 3.']
        figures = [f['figure_label'] for f in res]
        self.assertEqual(figures, expected_figures)
        # Finally remove the map file
        try:
            os.remove(map_file)
        except OSError:
           pass

@unittest.skip("skip update testing (arXiv)")
class TestARXIV(TestCase):

    '''Check arXiv processing'''

    def create_app(self):
        '''Create the wsgi application'''
        _app = app.create_app()
        _app.config['GRAPHICS_TMP_DIR'] = "%s/tests/stubdata" % PROJECT_HOME
        _app.config['GRAPHICS_IMAGE_DIR']= "%s/tests/stubdata/graphics" % PROJECT_HOME
        db.session = mock.Mock()
        first = db.session.query.return_value.filter.return_value.first
        first.return_value = None
        count = db.session.query.count
        count.return_value = 1
        return _app


    def test_ARXIV_update(self):
        '''Check update for an arXiv publication'''
        from utils import process_arXiv_graphics
        if not self.app.config.get('GRAPHICS_ENABLE_UPDATES', False):
            return True
        identifiers = [{'bibcode':'bibcode', 'arxid':'arXiv:YY.NN'}]
        st_dir  = "%s/tests/stubdata" % PROJECT_HOME
        # Put this map file in config 
        self.app.config['GRAPHICS_FULLTEXT_MAPS']['arXiv'] = st_dir
        # Now do an update
        res = process_arXiv_graphics(identifiers, False, dryrun=True)
        # We are expecting 9 figures
        self.assertEqual(len(res), 9)
        # Check if we get expected output
        figures = [f['figure_id'] for f in res]
        expected_figures = ['arxivYY.NN_f1', 'arxivYY.NN_f2', 'arxivYY.NN_f3',
                            'arxivYY.NN_f4', 'arxivYY.NN_f5', 'arxivYY.NN_f6',
                            'arxivYY.NN_f7', 'arxivYY.NN_f8', 'arxivYY.NN_f9']
        self.assertEqual(figures, expected_figures)
        # Clean up generated data
        try:
             shutil.rmtree(self.app.config.get('GRAPHICS_IMAGE_DIR'))
        except:
             pass
