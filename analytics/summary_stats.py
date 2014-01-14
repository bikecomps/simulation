#! /usr/bin/env python
'''
SummaryStats class used to generate bike trips and produce
stats about the bike trips:

- Maximum Duration Trip
- Minimum Duration Trip
- Average of Trip Times
- Standard Deviation of Trip Times
- Total Number of Trips Completed
- Total Number of Dissapointments

- Departures per Station
    station id => no. departures from station with that station id
- Arrivals per Station
    station id => no. arrivals from station with that station id

- Departures per Hour
    hour => no. departures completed that hour
- Arrivals per Hour
    hour => no. arrivals completed that hour

'''

from logic import PoissonLogic, Simulator
from utils import Connector
from models import Trip, Station

import csv
import datetime
import json
import numpy
import sys

class SummaryStats:
    def __init__(self, start_date, end_date):
        self.start_date = start_date
        self.end_date = end_date

        self.session = None
        self.trips = None
        self.disappointments = None

        self.stats = {}
        
        self.run_simulation()
        self.calculate_stats()

    def run_simulation(self):
        session = Connector().getDBSession()
        logic = PoissonLogic(session)
        simulator = Simulator(logic)
        results = simulator.run(self.start_date, self.end_date)

        self.session = session
        self.trips = results['trips']
        self.disappointments = results['dissapointments']

    def calculate_overall_stats(self):
        trips_and_times = [(trip.duration().total_seconds(), trip) for trip in self.trips]
        trip_times = [x[0] for x in trips_and_times]


        self.stats['total_num_trips'] = len(self.trips)
        self.stats['total_num_disappointments'] = len(self.disappointments)
        self.stats['avg_trip_time'] = numpy.average(trip_times)
        self.stats['std_trip_time'] = numpy.std(trip_times)        

        min_trip = min(trips_and_times)[1]
        max_trip = max(trips_and_times)[1]
        self.stats['min_duration_trip'] = {
            'start_station_id' : min_trip.start_station_id,
            'end_station_id' : min_trip.end_station_id,
            'start_datetime' : min_trip.start_date,
            'end_datetime' : min_trip.end_date,
            'duration' : min_trip.duration().total_seconds()
        }
        self.stats['max_duration_trip'] = {
            'start_station_id' : max_trip.start_station_id,
            'end_station_id' : max_trip.end_station_id,
            'start_datetime' : max_trip.start_date,
            'end_datetime' : max_trip.end_date,
            'duration' : max_trip.duration().total_seconds()
        }

    def calculate_per_station_stats(self):
        dep_counts = {}
        arr_counts = {}
        station_list = self.session.query(Station)

        for station in station_list:
            dep_counts[station.id] = 0
            arr_counts[station.id] = 0

        for trip in self.trips:
            dep_counts[trip.start_station_id] += 1
            arr_counts[trip.end_station_id] += 1

        self.stats['num_departures_per_station'] = dep_counts
        self.stats['num_arrivals_per_station'] = arr_counts


    def calculate_per_hour_stats(self):
        pass

    def calculate_stats(self):
        self.calculate_overall_stats()
        self.calculate_per_station_stats()
        self.calculate_per_hour_stats()
        
    def get_disappointments(self):
        return self.dump_json(self.disappointments)

    def get_stats(self):
        return self.dump_json(self.stats)
        
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
            raise TypeError, 'Cannot serialize item %s of type %s' % (repr(obj), type(obj))


def main():
    start_date = datetime.datetime.strptime('1-1-2012 00:00',
                                            '%m-%d-%Y %H:%M')
    end_date = datetime.datetime.strptime('1-2-2012 00:00',
                                          '%m-%d-%Y %H:%M')
                                          

    sstats = SummaryStats(start_date, end_date)

    print sstats.get_stats()

if __name__ == '__main__':
    main()
