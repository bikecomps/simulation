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
        self.full_station_disappointments = None
        self.empty_station_disappointments = None
        self.stats = {}
        self.station_name_dict = {}
        self.indent = False
        self.dis_station_counts = {}

        # option to run with range_evaluator
        self.run_evaluator = True

        self.run_simulation()
        self.calculate_stats()

    def run_simulation(self):
        options = {'station_caps' : self.capacity_dict}
        session = Connector().getDBSession()
        self.session = session
        #self.station_list = self.session.query(Station)

        # we only have 'real' trips up to the end of 2013
        # so we can't do comparisons/evaluations for 2014
        if self.run_evaluator and self.end_date.year <= 2013:
            re = RangeEvaluator(self.start_date, self.end_date, logic_options = options)
            self.stats['man_dist_score_arr'] = re.eval_man_indiv_dist(True)
            self.stats['man_dist_score_dep'] = re.eval_man_indiv_dist(False)
            self.stats['eucl_dist_score'] = re.eval_eucl_dist()

            self.trips = re.trips
            self.full_station_disappointments = re.full_station_disappointments
            self.empty_station_disappointments = re.empty_station_disappointments
            self.stats['final_station_counts'] = re.station_counts
            self.stats['simulated_station_caps'] = re.sim_station_caps
            self.arr_dis_station_counts = re.arr_dis_station_counts
            self.dep_dis_station_counts = re.dep_dis_station_counts
            self.station_list = self.session.query(Station).filter(Station.id.in_(re.station_counts.keys()))
        else:
            logic = PoissonLogic(session)
            simulator = Simulator(logic)            
            results = simulator.run(self.start_date, self.end_date, logic_options = options)            

            self.trips = results['trips']
            self.empty_station_disappointments = results['empty_station_disappointments']
            self.full_station_disappointments = results['full_station_disappointments']
            self.arr_dis_station_counts = results['arr_dis_stations']
            self.dep_dis_station_counts = results['dep_dis_stations']
            self.stats['final_station_counts'] = results['station_counts']
            self.stats['simulated_station_caps'] = results['sim_station_caps']
            self.station_list = self.session.query(Station).filter(Station.id.in_(results['station_counts'].keys()))

    def get_dummy_simulation(self):
        station_ids = [0,1,2,3,4]
        trip_list = []

        for i in range(22):
            start_time = datetime.datetime(2012, 1, 5, hour=i, minute=0, second=0, microsecond=0, tzinfo=None)
            end_time = datetime.datetime(2012, 1, 5, hour=i, minute=20, second=0, microsecond=0, tzinfo=None)
            trip_list.append(Trip(str(random.randint(1,500)),"Casual", 2,start_time,end_time,i%4,4-i%4))

        self.trips = trip_list
        self.full_station_disappointments = []
        self.empty_station_disappointments = []

    def calculate_overall_stats(self):
        trips_and_times = [(trip.duration().total_seconds(), trip) for trip in self.trips]
        trip_times = [x[0] for x in trips_and_times]
        self.stats['std_disappointments'] = {'total': numpy.std(self.stats['num_disappointments_per_station'].values()), 'dep': numpy.std(self.stats['num_dep_disappointments_per_station'].values()), 'arr': numpy.std(self.stats['num_arr_disappointments_per_station'].values())}
        self.stats['avg_disappointments'] = {'total': numpy.average(self.stats['num_disappointments_per_station'].values()), 'dep': numpy.average(self.stats['num_dep_disappointments_per_station'].values()), 'arr': numpy.average(self.stats['num_arr_disappointments_per_station'].values())}

        trips_per_station = dict([(a, self.stats["num_departures_per_station"][a] + self.stats["num_arrivals_per_station"][a]) for a in self.stats["num_arrivals_per_station"].keys()])
        self.stats['std_trips'] = {'total': numpy.std(trips_per_station.values()), 'dep': numpy.std(self.stats['num_departures_per_station'].values()), 'arr': numpy.std(self.stats['num_arrivals_per_station'].values())}
        self.stats['avg_trips'] = numpy.average(self.stats['num_departures_per_station'].values())
        self.stats['total_num_trips'] = len(self.trips)
        self.stats['total_num_disappointments'] = len(self.full_station_disappointments) + len(self.empty_station_disappointments)
        self.stats['total_num_full_disappointments'] = len(self.full_station_disappointments)
        self.stats['total_num_empty_disappointments'] = len(self.empty_station_disappointments)
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
        # disapointment counts per station
        #dis_counts = {}
        i = 0
        for station1 in self.station_list:
            i+=1
            station1_name = station1.name.encode('ascii', 'ignore')
            self.station_name_dict[station1.id] = station1_name

            dep_counts[station1_name] = 0
            arr_counts[station1_name] = 0            
 
            if station1.id not in self.arr_dis_station_counts: 
                self.arr_dis_station_counts[station1.id] = 0
 
            if station1.id not in self.dep_dis_station_counts: 
                self.dep_dis_station_counts[station1.id] = 0

            self.dis_station_counts[station1.id] = self.arr_dis_station_counts[station1.id] + self.dep_dis_station_counts[station1.id]
            
            pair_counts[station1_name] = {}
            for station2 in self.station_list:
                station2_name = station2.name.encode('ascii','ignore')
                pair_counts[station1_name][station2_name] = 0            
        print i, "in station_list"
        for trip in self.trips:
            start_station_name = self.station_name_dict[trip.start_station_id]
            end_station_name = self.station_name_dict[trip.end_station_id]
            dep_counts[start_station_name] += 1
            arr_counts[end_station_name] += 1
            pair_counts[start_station_name][end_station_name] += 1
        self.stats['station_name_dict'] = self.station_name_dict
        self.stats['num_departures_per_station'] = dep_counts
        self.stats['num_arrivals_per_station'] = arr_counts
        # self.stats['num_trips_per_pair_station'] = pair_counts
        self.stats['num_disappointments_per_station'] = self.dis_station_counts
        self.stats['num_dep_disappointments_per_station'] = self.dep_dis_station_counts 
        self.stats['num_arr_disappointments_per_station'] = self.arr_dis_station_counts
        self.stats['most_disappointing_dep_station'] = self.station_name_dict[max(self.dep_dis_station_counts, key = lambda x: self.dep_dis_station_counts[x])]
        self.stats['most_disappointing_arr_station'] = self.station_name_dict[max(self.arr_dis_station_counts, key = lambda x: self.arr_dis_station_counts[x])]


    def calculate_per_hour_stats(self):
        trip_counts = [[0,0] for i in range(24)]
        dis_time_counts = [0] * 24
        empty_dis_time_counts = [0] * 24
        full_dis_time_counts = [0] * 24

        for trip in self.trips:
            start_hour = trip.start_date.hour
            trip_counts[start_hour][0] += 1
            
            end_hour = trip.end_date.hour
            trip_counts[end_hour][1] += 1

        for disappointment in self.full_station_disappointments:
            hour = disappointment.time.hour
            dis_time_counts[hour] += 1
            full_dis_time_counts[hour] +=1

        for disappointment in self.empty_station_disappointments:
            hour = disappointment.time.hour
            dis_time_counts[hour] += 1
            empty_dis_time_counts[hour] +=1

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
        
        full_dis_time_counts_dict = [{
            "Hour" : i,
            "Number of Disappointments" : full_dis_time_counts[i]
        } for i in range(len(full_dis_time_counts))]
        
        empty_dis_time_counts_dict = [{
            "Hour" : i,
            "Number of Disappointments" : empty_dis_time_counts[i]
        } for i in range(len(empty_dis_time_counts))]
        
        self.stats['num_trips_per_hour'] = trip_counts_dict
        self.stats['num_disappointments_per_hour'] = dis_time_counts_dict
        self.stats['num_full_disappointments_per_hour'] = full_dis_time_counts_dict
        self.stats['num_empty_disappointments_per_hour'] = empty_dis_time_counts_dict


    def calculate_stats(self):
        # calculate station stats first so as to populate self.station_name_dict before calculating overall stats
        self.calculate_per_station_stats()
        print 'finished per_station_stats'
        self.calculate_overall_stats()
        print 'finished overall_stats'
        self.calculate_per_hour_stats()
        print 'finished per_hour_stats'
        
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
    sstats.indent = False
    result = sstats.get_stats()
    print len(result)

if __name__ == '__main__':
    main()
