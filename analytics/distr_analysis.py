#! /usr/bin/env python

from ..models import *
from ..utils import Connector

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def get_data_for_station_pair(session, station_one, station_two, date_one, date_two):
    values = session.query(Trip).filter(Trip.start_station_id==station_one) \
        .filter(Trip.end_station_id == station_two) \
        .filter(Trip.start_date.between(date_one, date_two))

    return values

def plot_distributions(results):
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

    trips = get_data_for_station_pair(session, 31000, 31001, "2012-1-1", "2013-1-1").all()
    plot_distributions(trips)

if __name__ == '__main__':
    main()
