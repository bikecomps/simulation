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
from dateutil import rrule
#from pybrain.datasets import SupervisedDataSet

Base = declarative_base()

def  get_num_days(start_date, end_date):
    """
    Return the number of days between 'start_date' and 'end_date'.
    Parameterize by 'year' -> 'month' -> 'part_of_week'.
    """
    start_year = start_date.year
    end_year = end_date.year    
    info = {}
    for year in range(start_year, end_year+1):
        info[year] = {}
        for i in range(1, 13):
            info[year][i] = [0]*2        

    for day in rrule.rrule(rrule.DAILY, dtstart=start_date, until=end_date):
        dow = day.weekday()
        index = 1 if dow < 5 else 0

        info[day.year][day.month][index] += 1        
    
    return info

def train_poisson(conn, start_d, end_d):
    '''
    Train parameters used to model poisson distributions
    representing bike activity between every pair of stations
    (could pair with self)
    '''
    a = datetime.strptime(start_d, '%Y-%m-%d')
    b = datetime.strptime(end_d, '%Y-%m-%d')
    num_days = (b-a).days
    if num_days < 1:
        print "You must train model using data for at least one day"
        return

    start_date = a
    end_date = b

    # start_year, end_year
    start_year = start_date.year
    end_year = end_date.year

    # get session and engine
    session = conn.getDBSession()
    engine = conn.getDBEngine()

    # cap the amount of results gotten; save memory
    cap = 10000

    t_hours = 24
    # (s1.id, s2.id) -> year -> month -> is_week_day 0 or 1 -> hour
    stationsd = {}

    stations = session.query(Station)
    for s1 in stations:
        for s2 in stations:
            stationsd[(s1.id, s2.id)] = {}
            for year in range(start_year, end_year+1):
                stationsd[(s1.id, s2.id)][year] = {}
                for month in range(1, 13):
                    stationsd[(s1.id, s2.id)][year][month] = [[0]*t_hours for i in range(2)]

    trip_num = 0
    for trip in session.query(Trip) \
            .filter(Trip.start_date.between(start_d, end_d)) \
            .yield_per(cap):
        s_id = trip.start_station_id
        e_id = trip.end_station_id

        month = trip.start_date.month
        year = trip.start_date.year
        hour = trip.start_date.hour
        dow = trip.start_date.weekday()

        stationsd[(s_id, e_id)][year][month][dow < 5][hour] += 1

        trip_num += 1

    # faster to delete all rows in the table
    session.query(Lambda).delete()

    count = 0
    days = get_num_days(start_date, end_date)

    for (s_id, e_id) in stationsd:
        counts = stationsd[(s_id, e_id)]

        for year in range(start_year, end_year+1):
            for month in range(1, 13):
                for is_week_day in range(2):
                    num_days = days[year][month][is_week_day]
                
                    for hour in range(t_hours):
                        num_trips = counts[year][month][is_week_day][hour]

                        if num_trips > 0:
                            l = Lambda(s_id, e_id, 
                                       hour, bool(is_week_day), 
                                       year, month,
                                       num_trips/float(num_days))
                            session.add(l)
                            count += 1

                        if count % cap == 0:
                            session.flush()
                            session.commit()
                
    # flush for last time
    session.flush()
    session.commit()

    print "Number of trips used in training: %d" % trip_num


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
    # get_pairwise_counts(c, "2013-1-1", "2013-1-2")
    # train_gammas(c.getDBSession(), "2010-09-15", "2013-06-30")
    train_poisson(c, "2010-09-15", "2013-06-30")

if __name__ == "__main__":
    main()
