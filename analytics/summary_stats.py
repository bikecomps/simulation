#! /usr/bin/env python
'''
SummaryStats class used to generate bike trips and produce
stats about the bike trips:

- Maximum Duration Trip
- Minimum Duration Trip
- Average of Trip Times
- Standard Deviation of Trip Times
- Total Number of Trips Completed
- Total Number of Disappointments

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
import random

class SummaryStats:
    def __init__(self, start_date, end_date, dummy = False):
        self.start_date = start_date
        self.end_date = end_date

        self.session = None
        self.trips = None
        self.disappointments = None
        self.stats = {}
    	self.station_name_dict = {}
        self.dummy = dummy
        self.indent = False

        if not dummy:
            self.run_simulation()
        else:
            self.get_dummy_simulation()
        self.calculate_stats()

    def run_simulation(self):
        session = Connector().getDBSession()
        logic = PoissonLogic(session)
        simulator = Simulator(logic)
        results = simulator.run(self.start_date, self.end_date)

        self.session = session
        self.trips = results['trips']
        self.disappointments = results['disappointments']

    def get_dummy_simulation(self):
        station_ids = [0,1,2,3,4]
        trip_list = []

        for i in range(22):
            start_time = datetime.datetime(2012, 1, 5, hour=i, minute=0, second=0, microsecond=0, tzinfo=None)
            end_time = datetime.datetime(2012, 1, 5, hour=i, minute=20, second=0, microsecond=0, tzinfo=None)
            trip_list.append(Trip(str(random.randint(1,500)),"Casual", 2,start_time,end_time,i%4,4-i%4))

        self.trips = trip_list
        self.disappointments = []


    def calculate_overall_stats(self):
        trips_and_times = [(trip.duration().total_seconds(), trip) for trip in self.trips]
        trip_times = [x[0] for x in trips_and_times]


        self.stats['total_num_trips'] = len(self.trips)
        self.stats['total_num_disappointments'] = len(self.disappointments)
        self.stats['avg_trip_time'] = numpy.average(trip_times)
        self.stats['std_trip_time'] = numpy.std(trip_times)        
        min_trip = 0 if len(trips_and_times) == 0 else min(trips_and_times)[1]
        max_trip = 0 if len(trips_and_times) == 0 else max(trips_and_times)[1]
        
        self.stats['min_duration_trip'] = {
            'start_station_name' : self.station_name_dict[min_trip.start_station_id].encode('ascii', 'ignore'),
            'end_station_name' : self.station_name_dict[min_trip.end_station_id].encode('ascii', 'ignore'),
            'start_datetime' : min_trip.start_date,
            'end_datetime' : min_trip.end_date,
            'duration' : min_trip.duration().total_seconds()
        }
        self.stats['max_duration_trip'] = {
            'start_station_name' : self.station_name_dict[max_trip.start_station_id].encode('ascii', 'ignore'),
            'end_station_name' : self.station_name_dict[max_trip.end_station_id].encode('ascii', 'ignore'),
            'start_datetime' : max_trip.start_date,
            'end_datetime' : max_trip.end_date,
            'duration' : max_trip.duration().total_seconds()
        }

    def calculate_per_station_stats(self):
        dep_counts = {}
        arr_counts = {}
        station_list = []
        if self.dummy:
            self.station_name_dict = {0:"17 & H Street",1:"Federal Circle Metro Station",2:"NW Hall Ave & 17th St",3:"SE 10th St & Minnesota",4:"Hell"}
            for s in self.station_name_dict:
                station_list.append(Station(s,self.station_name_dict[s],20,None))
                dep_counts[self.station_name_dict[s]] = 0
                arr_counts[self.station_name_dict[s]] = 0
        else:
            station_list = self.session.query(Station)

            for station in station_list:
                dep_counts[station.name.encode('ascii','ignore')] = 0
                arr_counts[station.name.encode('ascii','ignore')] = 0
                self.station_name_dict[station.id] = station.name

        for trip in self.trips:
            dep_counts[self.station_name_dict[trip.start_station_id]] += 1
            arr_counts[self.station_name_dict[trip.end_station_id]] += 1

        self.stats['num_departures_per_station'] = dep_counts
        self.stats['num_arrivals_per_station'] = arr_counts


    def calculate_per_hour_stats(self):
        list_counts = [[0,0] for i in range(24)]

        for trip in self.trips:
            start_hour = trip.start_date.hour
            list_counts[start_hour][0] += 1
            
            end_hour = trip.end_date.hour
            list_counts[end_hour][1] += 1

        # put in suitable form for group chart
        counts = [{
            "Hour": i,
            "Number of Departures" : list_counts[i][0],
            "Number of Arrivals" : list_counts[i][1]
        } for i in range(len(list_counts))]

        self.stats['num_trips_per_hour'] = counts

    def calculate_stats(self):
        # now important to calculate station stats first so as to populate self.station_name_dict before calculating overall stats
        self.calculate_per_station_stats()
        self.calculate_overall_stats()
        self.calculate_per_hour_stats()
        
    def get_disappointments(self):
        return self.dump_json(self.disappointments)

    def get_stats(self):
        return self.dump_json(self.stats)
        
    def dump_json(self, to_dump):
        '''
        Utility to dump json in nice way
        '''
        if self.indent:
            return json.dumps(to_dump, indent=4, default=self.json_dump_handler)
        else:
            return json.dumps(to_dump, default=self.json_dump_handler)
    
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
    sstats.indent = True
    print sstats.get_stats()

if __name__ == '__main__':
    main()
