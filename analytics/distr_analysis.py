#! /usr/bin/env python

from models import *
from utils import Connector

import numpy as np
import matplotlib
# matplotlib.use('Agg')
import matplotlib.pyplot as plt

allmeans = []
allstds = []

def get_data_for_station_pair(session, station_one, station_two, date_one, date_two):
    values = session.query(Trip).filter(Trip.start_station_id==station_one) \
        .filter(Trip.end_station_id == station_two) \
        .filter(Trip.start_date.between(date_one, date_two))

    return values

def num_departures_distributions(results):
    freqs = [0] * 24
    for trip in results:
        freqs[trip.start_date.hour] += 1
    x = np.array(freqs)

    mean = np.mean(x)
    var = np.var(x)
    allmeans.append(mean)
    allstds.append(var)
    print "mean=", mean
    print "var=", var

def num_arrivals_distributions(results):
    pass

def plot_time_distributions(results):
    trip_lengths = [trip.duration().total_seconds() for trip in results]
    num_bins = 50
    n, bins, patches = plt.hist(trip_lengths, num_bins, normed=1, facecolor='blue', alpha=0.5)
    plt.xlabel('Trip Times')
    plt.ylabel('Counts')
    plt.title('Test')
    plt.savefig('output.png')


def main():
    c = Connector()
    session = c.getDBSession()
    
    stations = session.query(Station).all()
    for s1 in stations:
        for s2 in stations:
            print "obtaining mean and std for s1=", s1.id, ";s2=", s2.id
            trips = get_data_for_station_pair(session, s1.id, s2.id, "2012-1-1", "2013-1-1").all()
            num_departures_distributions(trips)
    # trips = get_data_for_station_pair(session, 31248, 31206, "2012-1-1", "2013-1-1").all()
    # plot_time_distributions(trips)
    print "mean of means:", np.mean(np.array(allmeans))        
    print "mean of stds:", np.mean(np.array(allstds))
    # plot_num_arrivals_distributions(trips)

if __name__ == '__main__':
    main()
