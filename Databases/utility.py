#!/usr/bin/python
'''
Here, we put functions that we think could
be re-usable and useful. 
'''

import hidden
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

def getDBSession(e=False):
    engine_path = 'postgresql://%s:%s@localhost/%s' % (hidden.DB_USERNAME, hidden.DB_PASSWORD, hidden.DB_NAME)
    engine = create_engine(engine_path, echo=e)
    session_factory = sessionmaker(bind=engine)
    Session = scoped_session(session_factory)
    session = Session()
    return session

def getDBConnection(e=False):
    engine_path = 'postgresql://%s:%s@localhost/%s' % (hidden.DB_USERNAME, hidden.DB_PASSWORD, hidden.DB_NAME)
    engine = create_engine(engine_path, echo=e)
    connection = engine.connect()
    return connection
