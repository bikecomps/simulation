'''
Holds Analyzer class used to analyze results from, currently, a csv
representing trip objects.

Future: Grab from database?
'''
import csv
import csv
import datetime
import json
import numpy
import sys

from utility import Connector
from data_model import Trip, Station


class Analyzer:
    def __init__(self, session):
        self.session = session
        
    def read_and_parse(self, file_name):
        '''
        Parses trips from the given csv file and returns them as a list
        '''
        trip_list = []
        with open(file_name, 'r') as f:
            reader = csv.reader(f)
            for line in reader:
                bike_id = line[0]
                member_type = line[1]
                trip_type = line[2]
                output_type_one = "%Y-%m-%d %H:%M:%S.%f"
                output_type_two = "%Y-%m-%d %H:%M:%S"
                if "." in line[3]:
                    start_date =  datetime.datetime.strptime(line[3], output_type_one)
                else:
                    start_date =  datetime.datetime.strptime(line[3], output_type_two)

                if "." in line[4]:
                    end_date =  datetime.datetime.strptime(line[4], output_type_one)
                else:
                    end_date =  datetime.datetime.strptime(line[4], output_type_two)

                start_station_id = int(line[5])
                end_station_id = int(line[6])

                trip = Trip(bike_id, member_type, trip_type, start_date, end_date,
                            start_station_id, end_station_id)
                trip_list.append(trip)

        return trip_list

    
    def get_station_stats(self, trips):
        '''
        Gets station-wise trips
        '''
        stations = {}

        DEPARTURES = 'departures'
        ARRIVALS = 'arrivals'
        # Want stats for every station
        station_list = self.session.query(Station)

        for station in station_list:
            stations[station.id] = {}

        for trip in trips:
            station_departs = stations[trip.start_station_id].get(DEPARTURES, {})
            station_departs[trip.end_station_id] = station_departs.get(trip.end_station_id, []) + [trip.start_date]
            # Record a bit of meta-data about the arrival - we could easily do more
            stations[trip.start_station_id][DEPARTURES] = station_departs

            station_arrivals = stations[trip.end_station_id].get(ARRIVALS, {})
            station_arrivals[trip.start_station_id] = station_departs.get(trip.start_station_id, []) + [trip.end_date]
            stations[trip.end_station_id][ARRIVALS] = station_arrivals

        for station_id, station_info in stations.iteritems():            
            station_info['total_departures'] = len(station_info.get(DEPARTURES, []))
            station_info['total_arrivals'] = len(station_info.get(ARRIVALS, []))

        return self.dump_json(stations)


    def get_summary_stats(self, trips):
        '''
        Some pretty random general stats about trip arguments.
        '''
        stat_dict = {}
        stat_dict['total_trips'] = len(trips)
        
        trip_lengths = [trip.duration().total_seconds() for trip in trips]
        trip_times  = { 
                'average' : numpy.average(trip_lengths),
                'std' : numpy.std(trip_lengths),
        }
        
        max_length = max(trip_lengths)
        index = trip_lengths.index(max_length)
        max_trip = trips[index]

        max_trip_data = {
            'length' : max_length,
            'start_station' : max_trip.start_station_id,
            'end_station' : max_trip.end_station_id 
        }

        min_length = min(trip_lengths)
        index = trip_lengths.index(min_length)
        min_trip = trips[index]

        min_trip_data = {
            'length' : min_length,
            'start_station' : min_trip.start_station_id,
            'end_station' : min_trip.end_station_id 
        }
                

        trip_times['max'] = max_trip_data
        trip_times['min'] = min_trip_data
        stat_dict['trip_times'] = trip_times
       
        #TODO, more summary stats I suppose
        return self.dump_json(stats_dict)


    def dump_json(self, to_dump):
        '''
        Utility to dump json in nice way
        '''
        return json.dumps(to_dump, indent=4, default=self.json_dump_handler)
    
    def json_dump_handler(self, obj):
        '''
        Converts from python to json for some types, add more ifs for more cases

        Thanks to following site:
        http://stackoverflow.com/questions/455580/json-datetime-between-python-and-javascript
        '''
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        else:
            return TypeError, 'Cannot serialize item %s of type %s' % (repr(obj), type(obj))

def main():
    s = Connector().getDBSession()
    builder = Analyzer(s)
    trips = builder.read_and_parse(sys.argv[1])
    #builder.get_summary_stats(trips)
    print builder.get_station_stats(trips)


if __name__ == '__main__':
    main()
