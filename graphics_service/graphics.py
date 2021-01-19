'''
Created on Nov 2, 2014

@author: ehenneken
'''
from __future__ import absolute_import
import sys
import os
import simplejson as json
import random
from flask import current_app
#from models import AlchemyEncoder, GraphicsModel
from .models import get_graphics_record
#from sqlalchemy.orm.exc import NoResultFound

thumb_link = '<a href="%s" target="_new" border=0>' + \
            '<img src="%s" width="100px"></a>'
graph_link = '<a href="graphics" border=0><img src="%s"></a>'
ADSASS_img = '<img src="%s">'
ADSASS_thmb_img = '<img src="%s" width="100px">'
ADSASS_thmb_link = '<a href="graphics" border=0>%s</a>'
ADS_base_url = 'http://articles.adsabs.harvard.edu/cgi-bin/nph-iarticle_query'
ADS_image_url = ADS_base_url + \
    '?bibcode=%s&db_key=AST&page_ind=%s&data_type=GIF&type=SCREEN_VIEW'


def get_graphics(bibcode):
    # Query graphics database with bibcode supplied
    results = get_graphics_record(bibcode)

    if results and 'figures' in results:
        if len(results['figures']) == 0:
            # There are cases where an entry exists, but the 'figures'
            # list is empty. Report this as if no data exists.
            return {'Error': 'Unable to get results!', 'Error Info': 'No figure data for %s' % bibcode}
        eprint = results.get('eprint')
        source = results.get('source', 'NA')
        results['ADSlink'] = []
        if not eprint:
            results['figures'] = [a for a in results['figures'] if a['figure_label'] != None]
        display_figure = random.choice(results['figures'])
        results['pick'] = ''
        results['number'] = 0
        if source in current_app.config.get('GRAPHICS_EXTSOURCES'):
            # Non-AAS journals link to IOPscience, rather than AIE
            if source == "IOP" and bibcode[4:9] not in ['ApJ..','ApJS.','AJ...']:
                source = "IOPscience"
            header = current_app.config.get('GRAPHICS_HEADER').get(source,'')
            results['header'] =  header
            try:
                display_image = random.choice(display_figure['images'])
                thumb_url = display_image['thumbnail']
                results['pick'] = graph_link % thumb_url
            except:
                return {'Error': 'Unable to get results!', 'Error Info': 'Failed to get thumbnail for display image for %s' % bibcode}
            for figure in results['figures']:
                images = figure.get('images', [])
                results['number'] += len(images)
                for image in images:
                    thumb_url = image['thumbnail']
                    highr_url = image['highres']
        elif source.upper() == 'ARXIV' \
                and current_app.config.get('GRAPHICS_INCLUDE_ARXIV'):
            results['header'] = 'Images extracted from the arXiv e-print'
            try:
                display_image = random.choice(display_figure['images'])
                thumb_url = display_image['highres']
                results['pick'] = graph_link % thumb_url
            except:
                return {'Error': 'Unable to get results!', 'Error Info': 'Failed to get thumbnail for display image for %s' % bibcode}
            for figure in results['figures']:
                images = figure.get('images', [])
                results['number'] += len(images)
                for image in images:
                    thumb_url = image['thumbnail']
                    highr_url = image['highres']
        elif source.upper() == 'TEST':
            results['pick'] = display_figure
        else:
            results = {'Error': 'Unable to get results!', 'Error Info': 'Unknown data source %s' % source} 
        return results

    return results
