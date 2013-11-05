#!/usr/bin/python
'''
Used to train parameters for the distributions used to model
bike activity (number of departures/arrivals and trip times)
between every pair of stations.
'''

from data_model import *
from utility import Connector
from datetime import datetime
from sqlalchemy import update
from sqlalchemy.ext.declarative import declarative_base

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
    
    # faster to delete all rows in the table?
    session.query(Lambda).delete()

    count = 0
    for (s_id, e_id) in stationsd:
        counts = stationsd[(s_id, e_id)]
        for day in range(t_days):
            for hour in range(t_hours):               
                l = Lambda(s_id, e_id, hour+1, day+1, counts[day][hour]/float(numdays))
                session.add(l)
                count += 1

                if count % 1000 == 0:
                    session.flush()
                    session.commit()
                
    # flush for last time
    session.flush()
    session.commit()

    print "Number of trips used in training: %d" % tripnum
    print "Parameters trained for %d day(s)" % numdays

def main():
    c = Connector()

    train_poisson(c, "2012-1-1", "2012-1-2")

if __name__ == "__main__":
    main()
