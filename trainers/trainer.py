#!/usr/bin/env python
'''
Used to train parameters for the distributions used to model
bike activity (number of departures/arrivals and trip times)
between every pair of stations.
'''

from models import *
from utils import Connector

import math
from scipy.stats import gamma
from datetime import datetime
from sqlalchemy import update
from sqlalchemy.ext.declarative import declarative_base
import numpy
from pybrain.datasets import SupervisedDataSet

Base = declarative_base()

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


#http://stackoverflow.com/questions/16963415/why-does-the-gamma-distribution-in-scipy-have-three-parameters
#http://stackoverflow.com/questions/17814320/scipy-stats-meaning-of-parameters-for-probability-distributions
#http://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.gamma.html#scipy.stats.gamma
#http://stackoverflow.com/questions/18703262/using-python-scipy-to-fit-gamma-distribution-to-data
def train_gammas(session, start_date, end_date):
    session.query(Gamma).delete()

    trip_map = {}
    for trip in session.query(Trip) \
            .filter(Trip.start_date.between(start_date, end_date)):
        all_trip_times = trip_map.get((trip.start_station_id, trip.end_station_id), [])
        trip_time = (trip.end_date - trip.start_date).total_seconds()
        # Need to remove trip times of 0 to prevent math domain errors 
        if trip_time > 0:
            all_trip_times.append(trip_time)
        trip_map[(trip.start_station_id, trip.end_station_id)] = all_trip_times
    

    nans = 0
    non_nans = 0
    avg_num_trips = 0
    count = 0
    for (start_id, end_id), trip_times in trip_map.iteritems():
        #print numpy.average(trip_times)
        avg_num_trips += len(trip_times)
        count += 1
        try:
            shape, loc, scale = gamma.fit(trip_times, floc=0, fscale=1)
            #shape, scale = est_gamma(trip_times)
            #if shape == -1 or scale == -1:

            # If shape == 0 then for data x_0, x_1, .. x_i : x_0 = x_1 = x_i
            # If this is the case I'm just putting an about gaussian distr
            # about the mean. This can be achieved by shape=scale=sqrt(mean)
            if numpy.isnan(shape):
                shape = scale = math.sqrt(float(sum(trip_times)) / len(trip_times))
        # Should not happen now that I removed 0 trip lengths
        except ValueError:
            shape = scale = -1

        g = Gamma(start_id, end_id, shape, scale)
        session.add(g)
    session.commit()

def est_gamma(data):
    N = len(data) * 1.0
    summation = sum(data)

    # Wikipedia says this estimates k with 1.5%
    #http://en.wikipedia.org/wiki/Gamma_distribution#Maximum_likelihood_estimation
    try:
        s = math.log(summation / N) - sum([math.log(x) for x in data]) / N
        if s == 0:
            '''
            print math.log(summation/N)
            print sum([math.log(x) for x in data]) / N
            print data
            print summation
            print N
            '''
            print data
    except ValueError:
        # Math domain error
        print data
        return (-1,-1)
    # If S == 0 then for data x_0, x_1, .. x_i : x_0 = x_1 = x_i
    if s == 0:
        return (-1, -1)
    radicand = (s - 3) ** 2 + 24 * s
    if radicand < 0:
        print "Uh oh!"
        return (-1,-1)
    k = 3 - s + math.sqrt(radicand) / (12 * s)
    theta = 1.0 * summation / (k * N)
    return (k, theta)


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

def train_poisson_nn(conn, start_date, end_date):
    session = conn.getDBSession() 
   
    stations = session.query(Station) 
    station_dir = {}
    # We only care about neighborhoods that have stations in them
    neighbs = set()
    for station_1 in stations:
        for station_2 in stations:
            for day in xrange(6):
                for hour in xrange(24):
                    station_dir[(station_1, station_2)] = 0
        station_neighb = station_1.intersection.neighborhood

        if  station_neighb not in neighbs:
            neighbs.add(station_neighb)
  
    # Now create the dataset! Yay! 
    for neighb in neighbs:
        attrs = neighb.attrs
        num_attrs = len(attrs)
        print neighb.FIPS_code, attrs

    def get_pairwise_counts(conn, start_d, end_d):
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

def main():
    c = Connector()
    #train_gaussian(c, "2012-1-1", "2013-6-1")
    # train_poisson(c, "2012-1-1", "2013-1-1")
    #train_poisson_nn(c, 's','s')
    #get_pairwise_counts(c, "2013-1-1", "2013-1-2")
    train_gammas(c.getDBSession(), "2012-1-1", "2012-4-1")

if __name__ == "__main__":
    main()
