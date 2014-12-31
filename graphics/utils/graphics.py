'''
Created on Nov 2, 2014

@author: ehenneken
'''
import sys
import os
import simplejson as json
import random
from flask import current_app
from database import db, AlchemyEncoder, Graphics

thumb_link = '<a href="%s" target="_new" border=0><img src="%s" width="100px"></a>'
graph_link = '<a href="graphics" border=0><img src="%s"></a>'
ADSASS_img = '<img src="%s">'
ADSASS_thmb_img  = '<img src="%s" width="100px">'
ADSASS_thmb_link = '<a href="graphics" border=0>%s</a>'
ADS_image_url = 'http://articles.adsabs.harvard.edu/cgi-bin/nph-iarticle_query?bibcode=%s&db_key=AST&page_ind=%s&data_type=GIF&type=SCREEN_VIEW'

def get_graphics(bibcode):
    try:
        resp = db.session.query(Graphics).filter(Graphics.bibcode==bibcode).one()
        results = json.loads(json.dumps(resp, cls=AlchemyEncoder))
        results['query'] = 'OK'
    except Exception, err:
        results = {}
        results['query' ] = 'failed'
        if 'row' in str(err):
           results['error'] = 'no data' 
        else:
           results['error'] = err

    if results and 'figures' in results:
        eprint = results.get('eprint')
        source = results.get('source','NA')
        results['widgets'] = []
        results['ADSlink'] = []
        if not eprint:
            results['figures'] = filter(lambda a: a['figure_label'] != None, results['figures'])
        display_figure = random.choice(results['figures'])
        results['pick'] = ''
        results['number'] = 0
        if source == 'IOP':
            results['header'] = 'Every image links to the <a href="http://www.astroexplorer.org/" target="_new">IOP "Astronomy Image Explorer"</a> for more detail.'
            try:
                display_image = random.choice(display_figure['images'])
                thumb_url = display_image['thumbnail']
                results['pick'] = graph_link % thumb_url
            except:
                pass
            for figure in results['figures']:
                images = figure.get('images',[])
                results['number'] += len(images)
                for image in images:
                    thumb_url = image['thumbnail']
                    highr_url = image['highres']
                    results['widgets'].append('<div class="imageSingle"><div class="image">'+thumb_link % (highr_url,thumb_url.replace('_tb','_lr'))+'</div><div class="footer">'+figure['figure_label']+'</div></div>')
        elif source == 'ADSASS':
            results['header'] = 'Images from the <a href="http://www.adsass.org/" target="_new">ADS All Sky Survey</a>'
            try:
                thumb_img = ADSASS_thmb_img % display_figure['image_url']
                results['pick'] = ADSASS_thmb_link % thumb_img
            except:
                pass
            for figure in results['figures']:
                results['number'] += 1
                image = ADSASS_img % figure['image_url']
                ADSlink = ADS_image_url%(bibcode.replace('&','%26'),figure['page']-1)
                WWT_link = ''
                if 'WWT_url' in figure:
                    WWT_link = '<a href="%s" target="_new">WWT</a>' % figure['WWT_url'].replace('%26','+')
                image_context = '<a href="%s" target="_new">%s</a>' % (ADSlink,image)
                results['widgets'].append('<div class="imageSingle"><div class="image">'+image_context+'</div><div class="footer">'+figure['figure_label']+'&nbsp;'+WWT_link+'</div></div>')
                results['ADSlink'].append(ADS_image_url%(bibcode.replace('&','%26'),figure['page']-1))
        elif source.upper() == 'ARXIV' and current_app.config['INCLUDE_ARXIV']:
            results['header'] = 'Images extracted from the arXiv e-print'
            try:
                display_image = random.choice(display_figure['images'])
                thumb_url = display_image['highres']
                results['pick'] = graph_link % thumb_url
            except:
                pass
            for figure in results['figures']:
                images = figure.get('images',[])
                results['number'] += len(images)
                for image in images:
                    thumb_url = image['thumbnail']
                    highr_url = image['highres']
                    lowrs_url = image['lowres']
                    results['widgets'].append('<div class="imageSingle"><div class="image">'+thumb_link % (highr_url,highr_url)+'</div></div>')
        else:
            results = {}
    if not results:
        results = {}
    return results
