#!/usr/bin/env python
'''
Used to train parameters for the distributions used to model
bike activity (number of departures/arrivals and trip times)
between every pair of stations.
'''

from models import *
from utils import Connector

from collections import defaultdict
import math
from scipy.stats import gamma, kstest
from datetime import datetime, timedelta
from sqlalchemy import update, distinct
from sqlalchemy.sql import extract, func
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


def train_dest_distrs(session, start_d, end_d):
    '''
    Based on past observations distribute bikes depending on where they went previously
    If no observation for a station given a day/hour, distribute bike randomly across all stations
    '''
    start_date = datetime.strptime(start_d, '%Y-%m-%d')
    end_date = datetime.strptime(end_d, '%Y-%m-%d')

    # For efficiency load stationwise 
    station_ids = session.query(Station.id).all()
    num_stations = len(station_ids)

    num_days = float((end_date - start_date).days)
    if num_days < 0:
        return False
    session.query(DestDistr).delete()
    session.commit()
    print "Done deleting"

    stations_done = 0
    for s_id in station_ids:

        num_zero = 0
        non_zero = 0
        # index by hour, day, end_station -> num trips
        trip_map = [[defaultdict(int) for h in range(24)] for d in range(7)]

        q = session.query(Trip)\
                .filter(Trip.start_date.between(start_date, end_date))\
                .filter(Trip.start_station_id == s_id)\
                .join(Trip.trip_type, aliased=True)\
                .filter(TripType.trip_type == 'Training').yield_per(10000)
        for trip in q:
            trip_map[trip.start_date.weekday()][trip.start_date.hour][trip.end_station_id] += 1

        # Convert above to percentages:
        for i in range(len(trip_map)):
            day = trip_map[i]
            for j in range(len(day)):
                station_map = day[j]
                # Total values:
                total_num_trips = float(sum(station_map.itervalues()))
                for e_id in station_ids:
                    # We're booting this. Not putting in DB (too much space)
                    '''
                    if total_num_trips == 0:
                        # with 31101 -> hour 11,12 day 4
                        # give each station equal probability of being chosen
                        prob = 1.0 / num_stations
                    else:
                        prob = station_map.get(e_id, 0.0) / total_num_trips
                        print "Here?"
                    '''
                    # Don't put any 0 probs in the db for now
                    num_trips = station_map.get(e_id[0], 0.0)
                    if num_trips:
                        session.add(DestDistr(s_id, e_id[0], i, j, num_trips/total_num_trips))
                    #else:
                    #    print "Bad: ?",s_id,e_id,prob,total_num_trips
                    #    print station_map
                
                '''
                if total_num_trips == 0:
                    # give each station equal probability of being chosen
                    prob = 1.0 / num_stations
                    for e_id in station_ids:
                        #session.add(DestDistr(s_id, e_id, i, j, prob))
                        dd =DestDistr(s_id, e_id, i, j, prob)
                        session.add(dd)
                else:
                    for e_id in station_ids:
                        count = station_map.get(e_id, 0)
                        if count:
                            prob = count / total_num_trips
                            #session.add(DestDistr(s_id, e_id, i, j, prob))
                            dd =DestDistr(s_id, e_id, i, j, prob)
                            session.add(dd)
                '''
        session.commit()
        session.flush()
        stations_done += 1
        if stations_done % 10 == 0:
            print "Stations done",stations_done
  
def train_exp_lambdas(conn, start_d, end_d):
    engine = conn.getDBEngine()
    session = conn.getDBSession()

    session.query(ExpLambda).delete()
    raw_query = """
                SELECT EXTRACT(DOW FROM start_date), EXTRACT(HOUR FROM start_date), COUNT(*) 
                FROM trips 
                    WHERE start_date BETWEEN '{sd}' AND '{ed}' 
                          AND trip_type_id=1
                          AND start_station_id={sid}
                GROUP BY EXTRACT(DOW FROM start_date), EXTRACT(HOUR FROM start_date);
            """
    # Calculate the number of weekdays in a range, and weekend days
    # thanks http://stackoverflow.com/questions/3615375/python-count-days-ignoring-weekends
    start_date = datetime.strptime(start_d, '%Y-%m-%d')
    end_date = datetime.strptime(end_d, '%Y-%m-%d')

    day_generator = (start_date + timedelta(x + 1) for x in xrange((end_date - start_date).days + 1))
    num_weekdays = sum(day.weekday() < 5 for day in day_generator)
    num_weekend_days = (end_date - start_date).days - num_weekdays

    station_count = 0
    for s_id in session.query(Station.id).all():
        # 24 hours then [is a weekday, not a weekday]
        counts = [[0,0] for x in range(24)]
        
        query = raw_query.format(sd=start_d, ed=end_d, sid=s_id[0])
        for dow, hour, count in engine.execute(query):
            # Postgres does 0-6, sunday = 0
            if 0 < dow < 6:
                avg = float(count) / num_weekdays
            else:
                avg = float(count) / num_weekend_days
            counts[int(hour)][0 < dow < 6] = avg

        for i in range(24):
            # If hour is 0 then we've never observed a trip - don't add to db
            for j in range(2):
                if counts[i][j] > 0:
                    # Convert from rate in hours to rate in seconds
                    rate = 3600.0 / counts[i][j]
                    session.add(ExpLambda(s_id, bool(j), i, rate))
       
        session.commit()
        session.flush()
        station_count += 1
        if station_count % 10 == 0:
            print "Done with %s stations" % station_count
    # shouldn't be necessary but keep it there for now
    session.commit()
    session.flush()



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
            .filter(Trip.trip_type_id == 1) \
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
    # session.query(Lambda).delete()

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
                print "Error on s_id",s_id,", e_id",end_id,"with trips", trip_times,"resulting in shape, scale",shape,scale
                shape = scale = .0000001

            if shape < 0 or scale < 0:
                print "Fit gave negative values on on s_id",s_id,", e_id",end_id,"with trips", trip_times,"resulting in shape, scale",shape,scale
                shape = scale = .0000001

            g = Gamma(s_id, end_id, shape, scale)
            session.add(g)
        session.flush()
        session.commit()
        print "Trained station", s_id
             
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
    # first_data = "2013-06-01"
    # end_data = "2014-01-01"

    # s_test_date = "2011-09-12"
    # e_test_date = "2011-09-19" 
    # train_gaussian(c, "2012-1-1", "2013-6-1")
    # get_pairwise_counts(c, "2013-1-1", "2013-1-2")
    # train_exp_lambdas(c, first_data, end_data)
    #train_dest_distrs(c.getDBSession(), first_data, end_data)
    # train_gammas(c.getDBSession(), "2010-09-15", "2013-06-30")
    train_poisson(c, "2010-09-15", "2013-06-30")

if __name__ == "__main__":
    main()
