#! /usr/bin/env python

import datetime
from sqlalchemy import create_engine, Column, DateTime, Enum, Float, Integer, String, ForeignKey, Sequence, Index, Boolean, Sequence
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
        self.disappointments = []

    def duration(self):
        return self.end_date - self.start_date

    def __repr__(self):
        return 'bike id:%s, member type:%s, trip type:%s, start date:%s, end date:%s, start station id:%s, end station id:%s' % (self.bike_id, self.member_type, self.trip_type, self.start_date, self.end_date, self.start_station_id, self.end_station_id)

    def getDict(self):
        return {
            'bike_id' : self.bike_id,
            'member_type' : self.member_type,
            'trip_type' : self.trip_type,
            'start_datetime' : self.start_date,
            'end_datetime' : self.end_date,
            'start_station_id' : self.start_station_id,
            'end_station_id' : self.end_station_id,
            'duration' : self.duration()
         }

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
    is_week_day = Column(Boolean)
    year = Column(Integer)
    month = Column(Integer)
    value = Column(Float)

    def __init__(self, start_station_id, end_station_id, 
                 hour, is_week_day, year, month, 
                 val):
        self.start_station_id = start_station_id
        self.end_station_id = end_station_id

        self.year = year
        self.is_week_day = is_week_day
        self.hour = hour
        self.month = month
        self.value = val
    
    def __repr__(self):
        return 'start station id: %s, end station id: %s, year: %s, is_week_day: %s, hour: %d, value: %.2f'\
                 % (self.start_station_id, 
                    self.end_station_id, 
                    self.year,
                    self.is_week_day,
                    self.hour, 
                    self.value)

    def getDict(self):
        return {
            "start_station_id" : self.start_station_id,
            "end_station_id" : self.end_station_id,
            "year" : self.year,
            "hour" : self.hour,
            "is_week_day" : self.is_week_day,
            "value" : self.value
        }

class ExpLambda(Base):
    '''
    Separate table to store parameters for exponential
    distributions used to model the number of bike
    departures for each station
    at a specific hour in a given day of the week. 
    '''
    __tablename__ = 'exp_lambda_distrs'
    id = Column(Integer, Sequence('exp_lambda_id_seq'), primary_key=True)
    station_id = Column(Integer, ForeignKey('stations.id'), nullable=False)
    station = relationship('Station', foreign_keys=[station_id],
                                 backref=backref('exp_lambdas'))
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    is_week_day = Column(Boolean, nullable=False)
    hour = Column(Integer, nullable=False) # range 0-23
    rate = Column(Float, nullable=False)

    def __init__(self, station_id, year, month, is_week_day, hour, rate):
        self.station_id = station_id
        self.year = year
        self.month = month
        self.is_week_day = is_week_day
        self.hour = hour
        self.rate = rate
    
    def __repr__(self):
        return 'ExpLambda: station id: %s, year %r, month %r, weekday %r,\
                    hour: %s, rate: %.2f'\
                 % (self.station_id, self.year, self.month, 
                    self.is_week_day, self.hour, self.rate)

class DestDistr(Base):
    '''
    Separate table to store probability of going from start station to end station 
    at a specific hour in a given day of the week. 
    '''
    __tablename__ = 'dest_distrs'
    id = Column(Integer, Sequence('dest_distr_id_seq'), primary_key=True)
    start_station_id = Column(Integer, ForeignKey('stations.id'))
    start_station = relationship('Station', foreign_keys=[start_station_id],
                                 backref=backref('dest_distr_start'))

    end_station_id = Column(Integer, ForeignKey('stations.id'))
    end_station = relationship('Station', foreign_keys=[end_station_id], 
                               backref=backref('dest_distr_end'))


    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    is_week_day = Column(Boolean, nullable=False)
    hour = Column(Integer, nullable=False) # range 0-23
    prob = Column(Float, nullable=False)

    def __init__(self, start_station_id, end_station_id, year, month, 
                 is_week_day, hour, prob):
        self.start_station_id = start_station_id
        self.end_station_id = end_station_id
        self.year = year
        self.month = month
        self.is_week_day = is_week_day
        self.hour = hour
        self.prob = prob
    
    def __repr__(self):
        return 'Destination distribution: start station id: %s, end station id: %s, hour: %s, is week day?: %r, prob: %.4f'\
                 % (self.start_station_id, self.end_station_id, self.hour, self.is_week_day, self.prob)

class Gamma(Base):
    '''
    Table stores gamma distributions for each pairwise station.
    Important: Based on seconds!
    More Important: No gammas if there are no training data between the stations!
    '''
    __tablename__ = 'gamma_distrs'
    id = Column(Integer, Sequence('gamma_id_seq'), primary_key=True)

    start_station_id = Column(Integer, ForeignKey('stations.id'))
    start_station = relationship('Station', foreign_keys=[start_station_id],
                                 backref=backref('gamma_start'))

    end_station_id = Column(Integer, ForeignKey('stations.id'))
    end_station = relationship('Station', foreign_keys=[end_station_id], 
                               backref=backref('gamma_end'))

    # Also known as k
    shape = Column(Float)
    # Also known as theta
    scale = Column(Float)

    def __init__(self, s_id, e_id, sh, sc):
        self.start_station_id = s_id
        self.end_station_id = e_id
        self.shape = sh
        self.scale = sc

    def __repr__(self):
        return 'Gamma distr: s_id={s_id}, e_id={e_id}, shape={sh}, scale={sc}'\
                .format(s_id=self.start_station_id, e_id=self.end_station_id,
                        sh=self.shape, sc=self.scale)


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
    trip_type = Column(Enum(u'Training', u'Produced', u'Testing', u'Removed', u'ExtrapolationTesting', name='trip_type'), 
             default=u'Produced')

    produced_on = Column(DateTime)

    def __init__(self, trip_type):
        self.trip_type = trip_type
        self.produced_on = datetime.datetime.now() 

    def __repr__(self):
        return 'type: %r, produced_on %r' % (self.trip_type, self.produced_on)

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

class StatusGroup(Base):
    '''
    Save space and make grouping easier for station status groups
    '''
    __tablename__ = 'status_groups'
    id = Column(Integer, Sequence('status_groups_id_seq'), primary_key=True)
    time = Column(DateTime, unique=True, nullable=False)

    def __init__(self, time):
        self.time = time

    def __repr__(self):
        return 'Station status pulled: time %s' % time


class StationStatus(Base):
    '''
    The results of querying the capital bike share station status API should be
    stored in this table.
    '''
    __tablename__ = 'station_statuses'

    #id = Column(Integer, Sequence('station_statuses_id_seq'), primary_key=True)
    status_group_id = Column(Integer, ForeignKey('status_groups.id'), 
                             primary_key=True)
    status_group = relationship('StatusGroup', foreign_keys=[status_group_id],
                                backref=backref('statuses'))

    station_id = Column(Integer, ForeignKey('stations.id'), primary_key=True)
    station = relationship('Station', foreign_keys=[station_id],
               backref=backref('statuses'))

    #time = Column(DateTime)

    # Seems unncessary to keep both.. but they don't always match up
    bike_count = Column(Integer, nullable=False)
    empty_docks = Column(Integer, nullable=False)

    def __init__(self, group, station_id, bike_count, empties):
        self.status_group = group
        self.station_id = station_id
        self.bike_count = bike_count
        self.empty_docks = empties

    def __repr__(self):
        return 'Station status: s_id={s} time={t} count={c} empty={e}'\
                .format(s=self.station_id, t=self.time, c=self.bike_count, 
                        e=self.empty_docks)


class Disappointment(Base):
    __tablename__ = 'disappointments'
    id = Column(Integer, Sequence('disappointments_id_seq'), primary_key=True)
    # If trip_type is null then it was a disappointment when a user arrived 
    # but the station was empty.
    trip_id = Column(Integer, ForeignKey('trips.id'),nullable=True)
    trip = relationship('Trip', foreign_keys=[trip_id],
               backref=backref('disappointments'))

    station_id = Column(Integer, ForeignKey('stations.id'))
    station = relationship('Station', foreign_keys=[station_id],
               backref=backref('disappointments'))

    time = Column(DateTime)

    def __init__(self, station_id, time, trip_id):
        self.station_id = station_id
        self.time = time
        self.trip_id = trip_id 

    def __repr__(self):
        if self.trip_id:
            return 'Disappointment: Mid-trip at station {s} at time {t} on trip'\
                    ' {tr}'.format(s=self.station_id, t=self.time, tr=self.trip_id)
        return 'Disappointment: Arrival at station {s} at time {t}'\
                .format(s=self.station_id, t=self.time)


def main():
    c = Connector(echo=True)
    engine = c.getDBEngine()

    # Create all tables if we haven't already
    Base.metadata.create_all(engine)

    # Indices that we've created so far
    # Lambda Indexes
    lambda_index = Index('lambda_day_hour_index', Lambda.is_week_day, Lambda.hour, Lambda.month)
    lambda_day_index = Index('lambda_day_index', Lambda.is_week_day)
    lambda_hour_index = Index('lambda_hour_index', Lambda.hour)
    lambda_month_index = Index('lambda_month_index', Lambda.month)
    lambda_year_index = Index('lambda_year_index', Lambda.year)

    dd_day_index = Index('dest_distr_day_index', DestDistr.is_week_day)
    dd_hour_index = Index('dest_distr_hour_index', DestDistr.hour)

    #dd_day_index.create(engine)
    #dd_hour_index.create(engine)

    # For increasing speed of training
    trip_date_index = Index('trip_date_index', Trip.start_date)
    trip_start_station_index = Index('trip_start_station_index', Trip.start_station_id)
    trip_end_station_index = Index('trip_end_station_index', Trip.end_station_id)

if __name__ == '__main__':
    main()

