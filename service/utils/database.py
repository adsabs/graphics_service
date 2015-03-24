'''
Created on Nov 2, 2014

@author: ehenneken
'''

import simplejson as json
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.dialects import postgresql
from flask.ext.sqlalchemy import SQLAlchemy

db = SQLAlchemy()

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

class GraphicsModel(db.Model):
  __tablename__='graphics'
  __bind_key__ ='graphics'
  id = Column(Integer,primary_key=True)
  bibcode = Column(String,nullable=False,index=True)
  doi = Column(String)
  source = Column(String)
  eprint = Column(Boolean)
  figures = Column(postgresql.JSON)
  modtime = Column(DateTime)
