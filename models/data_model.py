#! /usr/bin/env python

'''
Basic demo of SQL-Alchemy ORM. Can be found on:

http://docs.sqlalchemy.org/en/rel_0_8/orm/tutorial.html

Sample output after done:

test_orm=# \dt
             List of relations
 Schema |     Name      | Type  |   Owner   
--------+---------------+-------+-----------
 public | intersections | table | bikecomps
 public | stations      | table | bikecomps
(2 rows)

test_orm=# select * from intersections
test_orm-# ;
 id | lat | lon 
----+-----+-----
  1 |  50 |  50
(1 row)

test_orm=# select * from stations;
 id |      name       | capacity | intersection_id 
----+-----------------+----------+-----------------
  1 | Fifth and Union |        5 |               1
(1 row)
'''

import datetime
from sqlalchemy import create_engine, Column, DateTime, Enum, Float, Integer, String, ForeignKey, Sequence
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref, sessionmaker, scoped_session

from utils import Connector

Base = declarative_base()

class Station(Base):
    '''
    Represents a Station object, stored in the 'stations' table.
    Define all columns here. Foreign key references Intersection.
    '''
    __tablename__ = 'stations'
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    capacity = Column(Integer)
    intersection_id = Column(Integer, ForeignKey('intersections.id'))
    intersection = relationship('Intersection',
                                backref=backref('stations'))

    def __init__(self, id, name, capacity, intersection):
        self.id = id
        self.name = name
        self.capacity = capacity
        self.intersection = intersection

    def __repr__(self):
        return 'station id: %s, station name: %s, capacity: %s' % (self.id, self.name, self.capacity)

class StationDistance(Base):
    '''
    Separate table which stores Manhattan distances between stations.
    '''
    __tablename__ = 'station_distances'
    station1_id = Column(Integer, primary_key=True)
    station2_id = Column(Integer, primary_key=True)
    distance = Column(Float)

    def __init__(self, s1, s2, dist):
        self.station1_id = s1
        self.station2_id = s2
        self.distance = dist

    def __repr__(self):
        return 'station1 id: %s, station2 id: %s, distance: %s' % (self.station1_id, self.station2_id, self.distance)


class Intersection(Base):
    '''
    Simple Intersection class stored in the intersections table.
    '''
    __tablename__ = 'intersections'
    id = Column(Integer, Sequence('inter_id_seq'), primary_key=True)
    lat = Column(Float)
    lon = Column(Float)
    # Ignoring Neighborhood for now
    neighborhood_id = Column(Integer, ForeignKey('neighborhoods.id'))
    neighborhood = relationship('Neighborhood',
                                backref=backref('intersections'))

    def __init__(self, lat, lon, neighborhood):
        self.lat = lat
        self.lon = lon
        self.neighborhood = neighborhood

class Neighborhood(Base):
    __tablename__ = 'neighborhoods'
    id = Column(Integer, Sequence('neigh_id_seq'), primary_key=True)
    # FIPS code uniquely identifies census tracts
    FIPS_code = Column(String(15))
    
    def __init__(self, FIPS_code):
        self.FIPS_code = FIPS_code

class RoadSegment(Base):
    __tablename__ = 'road_segments'
    id = Column(Integer, Sequence('road_seg_id_seq'), primary_key=True)
    name = Column(String(100))

    start_intersection_id = Column(Integer, ForeignKey('intersections.id'))
    start_intersection = relationship('Intersection', 
                                      foreign_keys=[start_intersection_id], 
                                      backref=backref('road_segments_out', order_by=name))

    end_intersection_id = Column(Integer, ForeignKey('intersections.id'))
    end_intersection = relationship('Intersection', 
                                    foreign_keys=[end_intersection_id], 
                                    backref=backref('road_segments_in', order_by=name))
    
    def __init__(self, name, start_intersection, end_intersection):
        self.name = name
        self.start_intersection = start_intersection
        self.end_intersection = end_intersection

class Trip(Base):
    '''
    Stores all trips from test data as well as created trip data
    '''
    __tablename__ = 'trips'
    id = Column(Integer, Sequence('trip_id_seq'), primary_key=True)
    bike_id = Column(String(100))
    member_type = Column(Enum(u'Casual', u'Registered', name='member_type'), 
                         default=u'Registered')

    trip_type_id = Column(Integer, ForeignKey('trip_types.id'))
    trip_type = relationship('TripType', foreign_keys=[trip_type_id],
                                 backref=backref('trips'))

    start_date = Column(DateTime)
    end_date = Column(DateTime)

    start_station_id = Column(Integer, ForeignKey('stations.id'))
    start_station = relationship('Station', foreign_keys=[start_station_id],
                                 backref=backref('trips_out'))

    end_station_id = Column(Integer, ForeignKey('stations.id'))
    end_station = relationship('Station', foreign_keys=[end_station_id], 
                               backref=backref('trips_in'))

    def __init__(self, bike_id, member_type, trip_type_id, start_date, end_date,
                 start_station_id, end_station_id):
        self.bike_id = bike_id
        self.member_type = member_type
        self.trip_type_id = trip_type_id
        self.start_date = start_date
        self.end_date = end_date
        self.start_station_id = start_station_id
        self.end_station_id = end_station_id

    def duration(self):
        return self.end_date - self.start_date

    def __repr__(self):
        return 'bike id:%s, member type:%s, trip type:%s, start date:%s, end date:%s, start station id:%s, end station id:%s' % (self.bike_id, self.member_type, self.trip_type, self.start_date, self.end_date, self.start_station_id, self.end_station_id)

    @staticmethod
    def csv_header():
        return 'bike_id, member_type, trip_type, start_date, end_date, start_station_id, end_station_id'

    def to_csv(self):
        return '%s,%s,%s,%s,%s,%s,%s' % (self.bike_id, self.member_type, self.trip_type, self.start_date, self.end_date, self.start_station_id, self.end_station_id)
   

class Day(Base):
    '''
    We're going to have to consider whether this class should exist, other information about it
    '''
    __tablename__ = 'days'
    date = Column(DateTime, primary_key=True)
    
    def __init__(self, date):
        self.date = date

class Lambda(Base):
    '''
    Separate table to store parameters for poisson
    distributions used to model the number of bike
    arrivals between every pair of stations
    at a specific hour in a given day of the week. 
    '''
    __tablename__ = 'lambdas'
    id = Column(Integer, Sequence('lambda_id_seq'), primary_key=True)
    start_station_id = Column(Integer, ForeignKey('stations.id'))
    start_station = relationship('Station', foreign_keys=[start_station_id],
                                 backref=backref('lambda_start'))

    end_station_id = Column(Integer, ForeignKey('stations.id'))
    end_station = relationship('Station', foreign_keys=[end_station_id], 
                               backref=backref('lambda_end'))
    hour = Column(Integer) # range 0-23
    day_of_week = Column(Integer) # range 0-6
    value = Column(Float)

    def __init__(self, start_station_id, end_station_id, hour, day, val):
        self.start_station_id = start_station_id
        self.end_station_id = end_station_id
        self.hour = hour
        self.day_of_week = day
        self.value = val
    
    def __repr__(self):
        return 'start station id: %s, end station id: %s, hour: %s, day of week: %s, value: %.2f' % (self.start_station_id, self.end_station_id, self.hour, self.day_of_week, self.value)

    def getDict(self):
        return {"start_station_id" : self.start_station_id,
                "end_station_id" : self.end_station_id,
                "hour" : self.hour,
                "day_of_week" : self.day_of_week,
                "value" : self.value}

class GaussianDistr(Base):
    '''
    Separate table to store parameters for poisson
    distributions used to model the number of bike
    arrivals between every pair of stations
    at a specific hour in a given day of the week. 
    '''
    __tablename__ = 'gaussian_distrs'
    id = Column(Integer, Sequence('gaussian_id_seq'), primary_key=True)

    start_station_id = Column(Integer, ForeignKey('stations.id'))
    start_station = relationship('Station', foreign_keys=[start_station_id],
                                 backref=backref('gaussian_start'))

    end_station_id = Column(Integer, ForeignKey('stations.id'))
    end_station = relationship('Station', foreign_keys=[end_station_id], 
                               backref=backref('gaussian_end'))

    mean = Column(Float)
    std = Column(Float)


    def __init__(self, start_station_id, end_station_id, mean, std):
        self.start_station_id = start_station_id
        self.end_station_id = end_station_id
        self.mean = mean
        self.std = std

    def __repr__(self):
        return 'start_station_id:%s, end_station_id:%s, mean:%s, std:%s' % (self.start_station_id, self.end_station_id, self.mean, self.std)

class TripType(Base):
    '''
    Records meta-data about the type of trip,
    should put w/e else we think could be useful in this class
    '''
    __tablename__ = 'trip_types'
    id = Column(Integer, Sequence('trip_type_id_seq'), primary_key=True)
    trip_type = Column(Enum(u'Training', u'Testing', u'Produced', name='trip_type'), 
             default=u'Produced')

    produced_on = Column(DateTime)

    def __init__(self, trip_type):
        self.trip_type = trip_type
        self.produced_on = datetime.datetime.now() 

    def __repr__(self):
        return 'type: %r, produced_on %r' % (self.type, self.produced_on)

class NeighborhoodAttr(Base):
    '''
    For storing various census based (or other type) of data. 
    The descriptor of what type it is (i.e. population, avg. income) will
    be stored with AttributeType objects.
    '''
    __tablename__ = 'neighb_attrs'

    # For now, we'll assume that we can make everything a float
    value = Column(Float, nullable=False)

    neighborhood_id = Column(Integer, ForeignKey('neighborhoods.id'),
                        primary_key=True)
    neighborhood = relationship('Neighborhood', foreign_keys=[neighborhood_id],
               backref=backref('attrs'))

    attr_type_id = Column(Integer, ForeignKey('attr_types.id'),
                        primary_key=True)
    attr_type = relationship('AttributeType', foreign_keys=[attr_type_id], 
               backref=backref('attrs'))


    
    def __init__(self, value, attr_type, neighborhood_id):
        self.value = value
        self.attr_type = attr_type
        self.neighborhood_id = neighborhood_id
        
    def __repr__(self):
        return 'Type: %r, Value: %r' % (self.attr_type, self.value)

class AttributeType(Base):

    __tablename__ = 'attr_types'
    id = Column(Integer, Sequence('attr_types_id_seq'), primary_key=True)
    descriptor = Column(String(100), nullable=False)

    def __init__(self, descriptor):
        self.descriptor = descriptor

    def __repr__(self):
        return 'Attribute type: %r' % self.descriptor

def main():
    c = Connector(echo=True)
    engine = c.getDBEngine()

    # Create all tables if we haven't already
    Base.metadata.create_all(engine)

if __name__ == '__main__':
    main()

