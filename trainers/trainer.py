#!/usr/bin/env python
'''
Used to train parameters for the distributions used to model
bike activity (number of departures/arrivals and trip times)
between every pair of stations.
'''

from models import *
from utils import Connector

import math
from scipy.stats import gamma, kstest
from datetime import datetime
from sqlalchemy import update
from sqlalchemy.ext.declarative import declarative_base
import numpy
from pybrain.datasets import SupervisedDataSet

Base = declarative_base()

def train_poisson_new(conn, start_d, end_d):
    print "training poisson parameters based on trip data from {0} and {1}".format(start_d, end_d)

    find_trips_query = """
    SELECT s_id, e_id, extract(dow from dt) as dow, hour, avg(cnt) as avg_cnt
    FROM
      (SELECT start_station_id as s_id, end_station_id as e_id,
              start_date::date as dt, extract(hour from start_date) as hour, 
              count(*) as cnt
      FROM  (SELECT * 
             FROM trips 
             WHERE start_date  BETWEEN '{0}' and '{1}'
                   AND trip_type_id = 1) as s1
      GROUP BY start_station_id, end_station_id, dt, hour) as s2
    GROUP BY s_id, e_id, dow, hour;
    """.format(start_d, end_d)
    
    session = conn.getDBSession()
    engine = conn.getDBEngine()

    print "deleting all rows in the Lambda table"
    # faster to delete all rows in the table
    session.query(Lambda).delete()

    cap = 10000
    print "executing the query: \n"
    print find_trips_query
    results = engine.execute(find_trips_query)
    count = 0

    for row in results:
        s_id = row["s_id"]
        e_id = row["e_id"]
        dow = row["dow"]
        hour = row["hour"]
        value = row["avg_cnt"]

        l = Lambda(s_id, e_id, int(hour), int(dow), value)
        session.add(l)
        count += 1
        
        if count % cap == 0:
            session.flush()
            session.commit()

    session.flush()
    session.commit()

def train_poisson(conn, start_d, end_d):
    '''
    Train parameters used to model poisson distributions
    representing bike activity between every pair of stations
    (could pair with self)
    '''
    a = datetime.strptime(start_d, '%Y-%m-%d')
    b = datetime.strptime(end_d, '%Y-%m-%d')
    numdays = (b-a).days
    if numdays < 1:
        print "You must train model using data for at least one day"
        return

    # get session and engine
    session = conn.getDBSession()
    engine = conn.getDBEngine()

    # cap the amount of results gotten; save memory
    cap = 10000

    t_hours = 24
    t_days = 7
    stationsd = {}

    stations = session.query(Station).yield_per(cap)
    for s1 in stations:
        for s2 in stations:
            stationsd[(s1.id, s2.id)] = [[0]*t_hours for i in range(t_days)]

    tripnum = 0
    for trip in session.query(Trip) \
            .filter(Trip.start_date.between(start_d, end_d)) \
            .yield_per(cap):
        s_id = trip.start_station_id
        e_id = trip.end_station_id
        hour = trip.start_date.hour
        day = trip.start_date.weekday()

        stationsd[(s_id, e_id)][day-1][hour-1] += 1

        tripnum += 1
    
    # faster to delete all rows in the table
    session.query(Lambda).delete()

    count = 0
    for (s_id, e_id) in stationsd:
        counts = stationsd[(s_id, e_id)]
        for day in range(t_days):
            for hour in range(t_hours):               
                l = Lambda(s_id, e_id, hour+1, day+1, counts[day][hour]/float(numdays))
                session.add(l)
                count += 1

                if count % cap == 0:
                    session.flush()
                    session.commit()
                
    # flush for last time
    session.flush()
    session.commit()

    print "Number of trips used in training: %d" % tripnum
    print "Parameters trained for %d day(s)" % numdays


def train_gammas(session, start_date, end_date):
    session.query(Gamma).delete()

    trip_map = {}
    
    # For efficiency load stationwise 
    s_ids = session.query(Station.id).all()

    for s_id in s_ids:
        trip_map = {}
        for trip in session.query(Trip)\
                .filter(Trip.start_date.between(start_date, end_date))\
                .filter(Trip.start_station_id == s_id)\
                .join(Trip.trip_type, aliased=True)\
                .filter(TripType.trip_type == 'Training'):

            all_trip_times = trip_map.get(trip.end_station_id, [])
            trip_time = (trip.end_date - trip.start_date).total_seconds()
            # Need to remove trip times of 0 to prevent math domain errors 
            if trip_time > 0:
                all_trip_times.append(trip_time)
            trip_map[trip.end_station_id] = all_trip_times

        for end_id, trip_times in trip_map.iteritems():
            try:
                shape, loc, scale = gamma.fit(trip_times, floc=0, fscale=1)

                # If shape == 0 then for data x_0, x_1, .. x_i : x_0 = x_1 = x_i
                # If this is the case I'm just putting an about gaussian distr
                # about the mean. This can be achieved by shape=scale=sqrt(mean)
                if numpy.isnan(shape):
                    shape = scale = math.sqrt(float(sum(trip_times)) / len(trip_times))
             # Should not happen now that I removed 0 trip lengths
            except ValueError:
                shape = scale = -1

            g = Gamma(s_id, end_id, shape, scale)
            session.add(g)
        session.flush()
        session.commit()
        print "Trained station",s_id
    
             
    session.flush()
    session.commit()

def train_gaussian(connector, start_date, end_date):
    '''
    Creates gaussian distr statistics based on day. 
    Simple mapping of station_from to station_to -> mean,stdev

    For now I didn't include stations where we don't have any trip data.
    I figured that was safer than having them both be 0, it's an easy 
    fix that I'd be happy to discuss.
    '''
    session = connector.getDBSession()
    session.query(GaussianDistr).delete()

    trip_map = {}
    for trip in session.query(Trip) \
            .filter(Trip.start_date.between(start_date, end_date)):

        all_trip_times = trip_map.get((trip.start_station_id, trip.end_station_id), [])
        trip_time = (trip.end_date - trip.start_date).total_seconds()
        all_trip_times.append(trip_time)
        trip_map[(trip.start_station_id, trip.end_station_id)] = all_trip_times

    count = 0
    for (station_one, station_two), times in trip_map.iteritems():
        average_time = numpy.average(times)
        stdv_time = numpy.std(times)
        gd = GaussianDistr(station_one, station_two, average_time, stdv_time)
        session.add(gd)

        count += 1
        if count % 1000 == 0:
            session.flush()
            session.commit()
            print "Flushing group %s" % count

    session.flush()
    session.commit()


def main():
    c = Connector()
    # train_gaussian(c, "2012-1-1", "2013-6-1")
    # train_poisson(c, "2012-1-1", "2013-1-1")
    # train_poisson_nn(c, 's','s')
    # get_pairwise_counts(c, "2013-1-1", "2013-1-2")
    train_gammas(c.getDBSession(), "2010-09-15", "2013-06-30")
    train_poisson_new(c, "2010-09-15 00:00", "2013-06-30 23:59")

if __name__ == "__main__":
    main()
