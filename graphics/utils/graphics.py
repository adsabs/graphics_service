'''
Created on Nov 2, 2014

@author: ehenneken
'''

# general module imports
import sys
import os
import simplejson as json
import random
from flask import current_app
# modules for querying PostgreSQL
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.dialects import postgresql
from flask.ext.sqlalchemy import SQLAlchemy

db = SQLAlchemy()

thumb_link = '<a href="%s" target="_new" border=0><img src="%s" width="100px"></a>'
graph_link = '<a href="graphics" border=0><img src="%s"></a>'
ADSASS_img = '<img src="%s">'
ADSASS_thmb_img  = '<img src="%s" width="100px">'
ADSASS_thmb_link = '<a href="graphics" border=0>%s</a>'
ADS_image_url = 'http://articles.adsabs.harvard.edu/cgi-bin/nph-iarticle_query?bibcode=%s&db_key=AST&page_ind=%s&data_type=GIF&type=SCREEN_VIEW'

class PostgresQueryError(Exception):
    pass

class AlchemyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj.__class__, DeclarativeMeta):
            # an SQLAlchemy class
            fields = {}
            for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata']:
                data = obj.__getattribute__(field)
                try:
                    json.dumps(data) # this will fail on non-encodable values, like other classes
                    fields[field] = data
                except TypeError:
                    fields[field] = None
            # a json-encodable dict
            return fields

        return json.JSONEncoder.default(self, obj)

class Graphics(db.Model):
  __tablename__='graphics'
  __bind_key__ = 'graphics_db'
  id = Column(Integer,primary_key=True)
  bibcode = Column(String,nullable=False,index=True)
  doi = Column(String)
  source = Column(String)
  eprint = Column(Boolean)
  figures = Column(postgresql.JSON)
  modtime = Column(DateTime)

def get_graphics(bibcode):
    session = db.session()
    try:
        resp = session.query(Graphics).filter(Graphics.bibcode==bibcode).one()
        results = json.loads(json.dumps(resp, cls=AlchemyEncoder))
    except:
        results = {}
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
