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

import hidden
from sqlalchemy import create_engine, Column, DateTime, Enum, Float, Integer, String, ForeignKey, Sequence
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref, sessionmaker, scoped_session

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
    station1_id = Column(Integer)
    station2_id = Column(Integer)
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
    population = Column(Integer)
    # Presumably some other data?
    
    def __init__(self, population):
        self.population = population

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
    trip_type = Column(Enum(u'Training', u'Testing', u'Produced', name='trip_type'), 
                       default=u'Produced')

    start_date = Column(DateTime)
    end_date = Column(DateTime)

    start_station_id = Column(Integer, ForeignKey('stations.id'))
    start_station = relationship('Station', foreign_keys=[start_station_id],
                                 backref=backref('trips_out'))

    end_station_id = Column(Integer, ForeignKey('stations.id'))
    end_station = relationship('Station', foreign_keys=[end_station_id], 
                               backref=backref('trips_in'))

    def __init__(self, bike_id, member_type, trip_type, start_date, end_date,
                 start_station_id, end_station_id):
        self.bike_id = bike_id
        self.member_type = member_type
        self.trip_type = trip_type
        self.start_date = start_date
        self.end_date = end_date
        self.start_station_id = start_station_id
        self.end_station_id = end_station_id

    def __repr__(self):
        return 'bike id:%s, member type:%s, trip type:%s, start date:%s, end date:%s, start station id:%s, end station id:%s' % (self.bike_id, self.member_type, self.trip_type, self.start_date, self.end_date, self.start_station_id, self.end_station_id)

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

def main():
    # Defaults to using psycopg2 drivers
    # We don't want to commit all of our passwords/usernames so we need to import them.
    # I'll email you all the appropriate hidden document if you want to run this file
    engine_path = 'postgresql://%s:%s@localhost/%s' % (hidden.DB_USERNAME, hidden.DB_PASSWORD, hidden.DB_NAME)
    engine = create_engine(engine_path, echo=True)    
    # Create all tables if we haven't already
    Base.metadata.create_all(engine)

if __name__ == '__main__':
    main()

