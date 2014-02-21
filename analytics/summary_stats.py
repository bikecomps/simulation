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
- Final Station Counts 
- Simulated Station Capacities 
'''

from logic import PoissonLogic, Simulator
from utils import Connector
from models import Trip, Station
from tests import RangeEvaluator

import csv
import datetime
import json
import numpy
import sys
import random

class SummaryStats:
    def __init__(self, start_date, end_date, capacity_dict):
        self.start_date = start_date
        self.end_date = end_date
	self.capacity_dict = capacity_dict

        self.session = None
        self.trips = None
        self.disappointments = None
        self.stats = {}
    	self.station_name_dict = {}
        self.indent = False

        # option to run with range_evaluator
        self.run_evaluator = True

        self.run_simulation()
        self.calculate_stats()

    def run_simulation(self):
        options = {'station_caps' : self.capacity_dict}
        session = Connector().getDBSession()
        self.session = session
        self.station_list = self.session.query(Station)

        if self.run_evaluator:
            re = RangeEvaluator(self.start_date, self.end_date, logic_options = options)
            self.stats['man_dist_score_arr'] = re.eval_man_indiv_dist(True)
            self.stats['man_dist_score_dep'] = re.eval_man_indiv_dist(False)
            self.stats['eucl_dist_score'] = re.eval_eucl_dist()

            self.trips = re.trips
            self.disappointments = re.disappointments
            self.stats['final_station_counts'] = re.station_counts
            self.stats['simulated_station_caps'] = re.sim_station_caps

        else:
            logic = PoissonLogic(session)
            simulator = Simulator(logic)            
            results = simulator.run(self.start_date, self.end_date, logic_options = options)            

            self.trips = results['trips']
            self.disappointments = results['disappointments']
            self.stats['final_station_counts'] = results['station_counts']
            self.stats['simulated_station_caps'] = results['sim_station_caps']

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
        pair_counts = {}
        dis_counts = {} # disaapointment counts

        for station1 in self.station_list:
            station1_name = station1.name.encode('ascii', 'ignore')
            self.station_name_dict[station1.id] = station1_name

            dep_counts[station1_name] = 0
            arr_counts[station1_name] = 0            
            dis_counts[station1_name] = 0

            pair_counts[station1_name] = {}
            for station2 in self.station_list:
                station2_name = station2.name.encode('ascii', 'ignore')
                pair_counts[station1_name][station2_name] = 0            

        for trip in self.trips:
            start_station_name = self.station_name_dict[trip.start_station_id]
            end_station_name = self.station_name_dict[trip.end_station_id]
            dep_counts[start_station_name] += 1
            arr_counts[end_station_name] += 1
            pair_counts[start_station_name][end_station_name] += 1

            
        for disappointment in self.disappointments:
            dis_counts[self.station_name_dict[disappointment.station_id]] += 1

        self.stats['num_departures_per_station'] = dep_counts
        self.stats['num_arrivals_per_station'] = arr_counts
        self.stats['num_trips_per_pair_station'] = pair_counts
        self.stats['num_disappointments_per_station'] = dis_counts
        self.stats['most_disappointing_station'] = max(dis_counts, key = lambda x: dis_counts[x])

    def calculate_per_hour_stats(self):
        trip_counts = [[0,0] for i in range(24)]
        dis_time_counts = [0] * 24

        for trip in self.trips:
            start_hour = trip.start_date.hour
            trip_counts[start_hour][0] += 1
            
            end_hour = trip.end_date.hour
            trip_counts[end_hour][1] += 1

        for disappointment in self.disappointments:
            hour = disappointment.time.hour
            dis_time_counts[hour] += 1

        # put in suitable form for group chart
        trip_counts_dict = [{
            "Hour": i,
            "Number of Departures" : trip_counts[i][0],
            "Number of Arrivals" : trip_counts[i][1]
        } for i in range(len(trip_counts))]
        dis_time_counts_dict = [{
            "Hour" : i,
            "Number of Disappointments" : dis_time_counts[i]
        } for i in range(len(dis_time_counts))]
        
        self.stats['num_trips_per_hour'] = trip_counts_dict
        self.stats['num_disappointments_per_hour'] = dis_time_counts_dict

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
    start_date = datetime.datetime.strptime('2012-02-02 00:00',
                                            '%Y-%m-%d %H:%M')
    end_date = datetime.datetime.strptime('2012-02-03 00:00',
                                          '%Y-%m-%d %H:%M')
                                          

    sstats = SummaryStats(start_date, end_date, {})
    sstats.indent = True
    print sstats.get_stats()

if __name__ == '__main__':
    main()
