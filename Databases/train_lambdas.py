#!/usr/bin/python
'''
Used to train parameters for the
poission distributions used to model
bike activity (departures) between
every pair of stations.
'''

from data_model import *
import utility
from datetime import datetime
from sqlalchemy import update, select
import numpy

def train(session, start_d, end_d):
    a = datetime.strptime(start_d, '%Y-%m-%d')
    b = datetime.strptime(end_d, '%Y-%m-%d')
    numdays = (b-a).days
    if numdays < 1:
        print "You must train model using data for at least one day"
        return

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
        hour = trip.end_date.hour
        day = trip.end_date.weekday()

        stationsd[(s_id, e_id)][day-1][hour-1] += 1

        tripnum += 1

    for (s_id, e_id) in stationsd:
        counts = stationsd[(s_id, e_id)]
        for day in range(t_days):
            for hour in range(t_hours):
                # make this update, instead of add
                session.add(Lambda(s_id, e_id, hour+1, day+1, counts[day][hour]/float(numdays)))

    session.commit()
    print "Number of trips used in training: %d" % tripnum
    print "Parameters trained for %d day(s)" % numdays




def train_mus(connection, start_date, end_date):
    '''
    Creates gaussian distr statistics based on day. 
    Simple mapping of station_from to station_to -> mean,stdev
    '''
    with connection.begin() as trans:
        trip_select = select([Trip]).\
            where(Trip.start_date >= start_date).\
            where(Trip.end_date < end_date)
        trip_list = connection.execute(trip_select)
                 
        trip_map = {}
        for trip in trip_list:
            all_trip_times = trip_map.get((trip.start_station_id, trip.end_station_id), [])
            trip_time = (trip.end_date - trip.start_date).total_seconds()
            all_trip_times.append(trip_time)
            trip_map[(trip.start_station_id, trip.end_station_id)] = all_trip_times
        trip_list.close()

        station_select = select([Station])
        station_list = connection.execute(station_select).fetchall()

        insert_list = []
        for station_one in station_list:
            for station_two in station_list:
                if (station_one.id, station_two.id) in trip_map:
                    times = trip_map[(station_one.id, station_two.id)]
                    average_time = numpy.average(times)
                    stdv_time = numpy.std(times)
                    insert_list.append({
                        "start_station_id":station_one.id, 
                        "end_station_id":station_two.id,
                        "mean":average_time, 
                        "std":stdv_time}
                        )

        connection.execute(GaussianDistr.insert(), insert_list)

def main():
    s = utility.getDBSession()
    conn = utility.getDBConnection()
    train_mus(conn, "2012-1-1", "2012-1-2")


if __name__ == "__main__":
    main()
