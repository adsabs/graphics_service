'''
Created on Nov 2, 2014

@author: ehenneken
'''
import sys
import os
import simplejson as json
import random
from flask import current_app
from models import db, AlchemyEncoder, GraphicsModel
from sqlalchemy.orm.exc import NoResultFound

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
    try:
        resp = db.session.query(GraphicsModel).filter(
            GraphicsModel.bibcode == bibcode).one()
        results = json.loads(json.dumps(resp, cls=AlchemyEncoder))
        results['query'] = 'OK'
    except NoResultFound:
        results = {
            'query': 'failed',
            'error': 'no database entry found for %s' % bibcode}
    except (ValueError, TypeError), err:
        # Exception thrown when there is a problem with the JSON handling
        results = {'query': 'failed', 'error': 'JSON problem (%s)' % err}
        raise
    except Exception, err:
        if 'row' in str(err):
            results = {
                'query': 'failed',
                'error': 'no database entry found for %s' % bibcode}
        else:
            results = {
                'query': 'failed', 'error': 'PostgreSQL problem (%s)' % error}
    if results and 'figures' in results:
        if len(results['figures']) == 0:
            # There are cases where an entry exists, but the 'figures'
            # list is empty. Report this as if no data exists.
            results['query'] = 'failed'
            results['error'] = 'no data found for %s' % bibcode
            return results
        eprint = results.get('eprint')
        source = results.get('source', 'NA')
        results['ADSlink'] = []
        if not eprint:
            results['figures'] = filter(
                lambda a: a['figure_label'] != None, results['figures'])
        display_figure = random.choice(results['figures'])
        results['pick'] = ''
        results['number'] = 0
        if source in current_app.config.get('GRAPHICS_EXTSOURCES'):
            header = current_app.config.get('GRAPHICS_HEADER').get(source,'')
            results['header'] =  header
            try:
                display_image = random.choice(display_figure['images'])
                thumb_url = display_image['thumbnail']
                results['pick'] = graph_link % thumb_url
            except:
                pass
            for figure in results['figures']:
                images = figure.get('images', [])
                results['number'] += len(images)
                for image in images:
                    thumb_url = image['thumbnail']
                    highr_url = image['highres']
        elif source == 'ADSASS':
            results['header'] = 'Images from the ' + \
              '<a href="http://www.adsass.org/" target="_new">' + \
              'ADS All Sky Survey</a>'
            try:
                thumb_img = ADSASS_thmb_img % display_figure['image_url']
                results['pick'] = ADSASS_thmb_link % thumb_img
            except:
                pass
            for figure in results['figures']:
                results['number'] += 1
                image = ADSASS_img % figure['image_url']
                ADSlink = ADS_image_url % (
                    bibcode.replace('&', '%26'), figure['page'] - 1)
                WWT_link = ''
                if 'WWT_url' in figure:
                    WWT_link = '<a href="%s" target="_new">WWT</a>' % figure[
                        'WWT_url'].replace('%26', '+')
                image_context = '<a href="%s" target="_new">%s</a>' % (
                    ADSlink, image)
                results['ADSlink'].append(
                    ADS_image_url % (
                        bibcode.replace('&', '%26'), figure['page'] - 1))
        elif source.upper() == 'ARXIV' \
                and current_app.config.get('GRAPHICSINCLUDE_ARXIV'):
            results['header'] = 'Images extracted from the arXiv e-print'
            try:
                display_image = random.choice(display_figure['images'])
                thumb_url = display_image['highres']
                results['pick'] = graph_link % thumb_url
            except:
                pass
            for figure in results['figures']:
                images = figure.get('images', [])
                results['number'] += len(images)
                for image in images:
                    thumb_url = image['thumbnail']
                    highr_url = image['highres']
                    lowrs_url = image['lowres']
        elif source.upper() == 'TEST':
            results['pick'] = display_figure
            return results
        else:
            results = {}
    if not results:
        results = {
            'query': 'failed',
            'error': 'no database entry found for %s' % bibcode}
    return results
