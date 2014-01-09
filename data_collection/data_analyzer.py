#! /usr/bin/env python

import re
import sys
import numpy

#[now, station_id, num_bikes, num_empties]

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
    for time, time_stats in stats.iteritems():
        print "Time: %s" % time
        for station_name, station_data in time_stats.iteritems():
            avg_bike_count = numpy.average(station_data.get('num_bikes', []))
            std_bike_count = numpy.std(station_data.get('num_bikes', []))

            avg_empty_count = numpy.average(station_data.get('num_empties', []))
            std_empty_count = numpy.std(station_data.get('num_empties', []))
            
            
            print "\tStation: %s" % station_name
            print "\t\tAvg Count: %s" % avg_bike_count
            print "\t\tStdev count: %s" % std_bike_count
            print "\t\tAvg Empties: %s" % avg_empty_count
            print "\t\tStdev empties: %s" % std_empty_count


def parse_data(data):
    '''
    Parses from file, returning it as a multilayered dict.
    '''
    bike_stats = {}

    data = [line.split(',') for line in data]
    # Pull the hour at which the data was grabbed
    hour_match = re.compile('\d\d:')
    for line in data:
        if int(hour_match.findall(line[0])[0][:-1]) > 5:
            stats = bike_stats.get('Night', {})
            bike_stats['Night'] = stats
        else:
            stats = bike_stats.get('Morning', {})
            bike_stats['Morning'] = stats

        station_data = stats.get(line[1], {})
        stats[line[1]] = station_data

        bike_counts = station_data.get('num_bikes', [])
        bike_counts.append(int(line[2]))
        station_data['num_bikes'] = bike_counts

        empty_counts = station_data.get('num_empties', [])
        empty_counts.append(int(line[3]))
        station_data['num_empties'] = empty_counts 
        
    return bike_stats
        
def main():
    data = read(sys.argv[1])
    stats = parse_data(data)
    print_stats(stats)

if __name__ == '__main__':
    main()
