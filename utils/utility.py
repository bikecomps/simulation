#!/usr/bin/env python
'''
Here, we put functions that we think could
be re-usable and useful. 
'''

try:
    import hidden
except ImportError, e:
    exit("hidden.py must be in the same directory as utility.py")
    
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import os
import sys

class Connector:
    def __init__(self, echo=False):
        engine_path = 'postgresql://%s:%s@localhost/%s' % (hidden.DB_USERNAME, hidden.DB_PASSWORD, hidden.DB_NAME)
        engine = create_engine(engine_path, echo=echo)
        session_factory = sessionmaker(bind=engine)
        Session = scoped_session(session_factory)
        session = Session()

        self.engine = engine
        self.session = session

    def getDBSession(self):
        return self.session

    def getDBEngine(self):
        return self.engine

