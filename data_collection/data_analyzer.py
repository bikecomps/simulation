#! /usr/bin/env python

import re
import sys
import numpy
from datetime import datetime
from models import *
from utils import Connector

def read(filename):
    '''
    Read and return file
    '''
    with open(filename, 'r') as f:
        return f.readlines() 
    
def print_stats(stats):
    '''
    Expects a dictionary of times keyed to dicts of station ids with
    bike counts and emptycounts as subdictionaries.
    Prints summary stats about each station
    '''
    print "station_id, avg_num_bikes, std_num_bikes, avg_empty_count, std_empty_count"
    for time, time_stats in stats.iteritems():
        print "Time: %s" % time
        for station_name, station_data in time_stats.iteritems():
            avg_bike_count = numpy.average(station_data.get('num_bikes', []))
            std_bike_count = numpy.std(station_data.get('num_bikes', []))

            avg_empty_count = numpy.average(station_data.get('num_empties', []))
            std_empty_count = numpy.std(station_data.get('num_empties', []))
            
            
            print "%s,%s,%s,%s,%s" % (station_name, avg_bike_count, 
                           std_bike_count, avg_empty_count, std_empty_count)

def calc_stats(station_stats):
    stats = {}
    for time, time_stats in station_stats.iteritems():
        stats[time] = {}
        for station_name, station_data in time_stats.iteritems():
            avg_bike_count = numpy.average(station_data.get('num_bikes', []))
            std_bike_count = numpy.std(station_data.get('num_bikes', []))

            avg_empty_count = numpy.average(station_data.get('num_empties', []))
            std_empty_count = numpy.std(station_data.get('num_empties', []))
            
            stats[time][station_name] = {'avg_count':avg_bike_count,
                                         'std_count':avg_empty_count}

    return stats


def load_csv_to_db(session, csv):
    data = [line.split(',') for line in csv]
    stations = {s.id for s in session.query(Station)}
    for line in data:
        time = datetime.datetime.strptime(line[0], '%Y-%m-%d %H:%M:%S.%f')
        s_id = int(line[1])
        bike_count = int(line[2])
        empty_count = int(line[3])
        if s_id in stations:
            ss = StationStatus(s_id, time, bike_count, empty_count)
            session.add(ss)
        else:
            print "Error, no station ", s_id
    
    session.commit() 

def parse_data(data):
    '''
    Parses from file, returning it as a multilayered dict.
    '''
    bike_stats = {}

    data = [line.split(',') for line in data]
    # Pull the hour at which the data was grabbed
    hour_match = re.compile('\d\d:')
    for line in data:
        #hour = int(hour_match.findall(line[0])[0][:-1])
        time = line[0]
        stats = bike_stats.get(time, {})
        bike_stats[time] = stats

        station_data = stats.get(line[1], {})
        stats[line[1]] = station_data

        bike_counts = station_data.get('num_bikes', [])
        bike_counts.append(int(line[2]))
        station_data['num_bikes'] = bike_counts

        empty_counts = station_data.get('num_empties', [])
        empty_counts.append(int(line[3]))
        station_data['num_empties'] = empty_counts 
        
    return bike_stats

def get_total_num_bikes():
    '''
    Given a way to access the DB grab the max number of bikes at the stations
    that we've checked so far.
    '''
    # Check the days we have  and grab the most count
    # provides a good upperbound on the total number of bikes

    #TODO figure out a better way of doing this
    conn = Connector().getDBEngine().connect()
    sql_query = 'SELECT MAX(counts.sum) FROM (\
                            SELECT SUM(bike_count)\
                            FROM %s\
                            GROUP BY time) as counts' % StationStatus.__tablename__

    max_bike_count = conn.execute(sql_query).first()[0]
    return max_bike_count
        
def main():
    #data = read(sys.argv[1])
    #stats = parse_data(data)
    #print_stats(stats)
    #session = Connector().getDBSession()
    #load_csv_to_db(session, data)
    get_total_num_bikes()

if __name__ == '__main__':
    main()
