'''
Created on Nov 2, 2014

@author: ehenneken
'''

import simplejson as json
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.dialects import postgresql
from flask_sqlalchemy import SQLAlchemy
from flask import current_app

Base = declarative_base()

class AlchemyEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj.__class__, DeclarativeMeta):
            # an SQLAlchemy class
            fields = {}
            for field in [x for x in dir(obj)
                          if not x.startswith('_') and x != 'metadata']:
                data = obj.__getattribute__(field)
                try:
                    # this will fail on non-encodable values, like other
                    # classes
                    json.dumps(data)
                    fields[field] = data
                except TypeError:
                    fields[field] = None
            # a json-encodable dict
            return fields

        return json.JSONEncoder.default(self, obj)


class GraphicsModel(Base):
    __tablename__ = 'graphics'
    id = Column(Integer, primary_key=True)
    bibcode = Column(String, nullable=False, index=True)
    doi = Column(String)
    source = Column(String)
    eprint = Column(Boolean)
    figures = Column(postgresql.JSON)
    thumbnails = Column(postgresql.ARRAY(String), default=[])
    baseurl = Column(String)
    modtime = Column(DateTime)

def execute_SQL_query(bibc):
    with current_app.session_scope() as session:
        resp = session.query(GraphicsModel).filter(
             GraphicsModel.bibcode == bibc).one()
        results = json.loads(json.dumps(resp, cls=AlchemyEncoder))
        return results

def get_graphics_record(bibcode):
    try:
        res = execute_SQL_query(bibcode)
    except NoResultFound:
        res = {'Error': 'Unable to get results!', 'Error Info': 'No database entry found for %s' % bibcode}
    except Exception as err:
        res = {'Error': 'Unable to get results!', 'Error Info': 'Graphics query failed for %s: %s'%(bibcode, err)}
    return res
