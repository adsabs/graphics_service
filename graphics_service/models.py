'''
Created on Nov 2, 2014

@author: ehenneken
'''

import simplejson as json
from sqlalchemy import Column, Integer, String, DateTime, Boolean, or_
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
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
    scix_id = Column(String(19), nullable=True, unique=True, index=True)
    doi = Column(String)
    source = Column(String)
    eprint = Column(Boolean)
    figures = Column(postgresql.JSON)
    thumbnails = Column(postgresql.ARRAY(String), default=[])
    baseurl = Column(String)
    modtime = Column(DateTime)

def execute_SQL_query(ident):
    with current_app.session_scope() as session:
        # Filter against both scix_id and bibcode columns for backwards compatibility
        resp = session.query(GraphicsModel).filter(
             or_(GraphicsModel.scix_id == ident, GraphicsModel.bibcode == ident)).one()
        results = json.loads(json.dumps(resp, cls=AlchemyEncoder))
        return results

def get_graphics_record(identifier):
    try:
        res = execute_SQL_query(identifier)
    except NoResultFound:
        res = {'Error': 'Unable to get results!', 'Error Info': 'No database entry found for %s' % identifier}
    except MultipleResultsFound:
        res = {'Error': 'Unable to get results!', 'Error Info': 'Multiple results were found for %s' % identifier}
    except Exception as err:
        res = {'Error': 'Unable to get results!', 'Error Info': 'Graphics query failed for %s: %s'%(identifier, err)}
    return res
