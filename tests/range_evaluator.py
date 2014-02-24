#! /usr/bin/env python
"""
This 'evaluator' is used to print either the euclidean or manhattan
distance between the vector of produced trips and the vector of
real trips.
"""

from logic import ExponentialLogic, PoissonLogic, Simulator, AltPoissonLogic
from utils import Connector
from models import Trip, Station

from datetime import datetime
from dateutil import rrule

import numpy as np

import sys
import random

class RangeEvaluator:
    def __init__(self, start_date, end_date, logic_options = {}):
        year = end_date.year
        if year > 2013:
            print "We don't have testing data for 2014 and beyond"
            exit()

        self.start_date = start_date
        self.end_date = end_date
        self.logic_options = logic_options

        # by default, evaluator is not verbose
        self.verbose = False

        c = Connector()
        self.session = c.getDBSession()
        self.engine = c.getDBEngine()

        # store produced and real trips in dictionaries
        # station id -> [number of departures, number of arrivals]
        produced, total_produced, total_full_dp, total_empty_dp  = self.get_produced_trips()
        real, total_real = self.get_real_trips()

        self.station_ids = []
        self.produced = []
        self.real = []
        for k in produced:
            self.station_ids.append(k)
            self.produced.append(produced[k])
            self.real.append(real[k])
        print "----------------------------------------------"
        print "From:", datetime.strftime(start_date, "%Y-%m-%d %H:%M")
        print "To:", datetime.strftime(end_date, "%Y-%m-%d %H:%M")
        print "total produced: ", total_produced
        print "total disappointments: ", total_full_dp + total_empty_dp
        print "total arrival disappointments: ", total_full_dp
        print "total departure disappointments: ", total_empty_dp
        print "total real: ", total_real

    def get_produced_trips(self):
        # logic = PoissonLogic(self.session)
        #logic = ExponentialLogic(self.session)
        logic = AltPoissonLogic(self.session)
        simulator = Simulator(logic)
        results = simulator.run(self.start_date, self.end_date,
                                logic_options = self.logic_options)
        
        self.trips = results['trips']
        self.full_station_disappointments = results['full_station_disappointments']
        self.empty_station_disappointments = results['empty_station_disappointments']
        self.station_counts = results['station_counts']
        self.sim_station_caps = results['sim_station_caps']
        self.arr_dis_station_counts = results['arr_dis_stations']
        self.dep_dis_station_counts = results['dep_dis_stations']

        total_trips = 0

        trips = {}
        for trip in results['trips']:
            trips.setdefault(trip.start_station_id, [0, 0])
            trips.setdefault(trip.end_station_id, [0, 0])

            trips[trip.start_station_id][0] += 1
            trips[trip.end_station_id][1] += 1

            total_trips += 1

        return trips, total_trips, len(self.full_station_disappointments), len(self.empty_station_disappointments)
        
    def get_real_trips(self):
        start_date_string = self.start_date.strftime('%Y-%m-%d %H:%M')
        end_date_string = self.end_date.strftime('%Y-%m-%d %H:%M')

        trips = {}
        station_list = self.session.query(Station)
        for station in station_list:
            trips[station.id] = [0, 0]
        
        counts_query = """        
        SELECT start_station_id as id1, end_station_id as id2, c1, c2 
        FROM 
          (SELECT start_station_id, count(*) as c1 
          FROM trips
          WHERE start_date between '{0}' and '{1}' 
          GROUP BY start_station_id) as s1
          FULL OUTER JOIN
          (SELECT end_station_id, count(*) as c2 
          FROM trips
          WHERE end_date between '{0}' and '{1}' 
          GROUP BY end_station_id) as s2
          ON (start_station_id = end_station_id);
        """.format(start_date_string, end_date_string)

        results = self.engine.execute(counts_query)
        total_trips = 0
        for row in results:
            id = row["id1"] if row["id1"] else row["id2"]
            dep_counts = row["c1"] if row["c1"] else 0
            arr_counts = row["c2"] if row["c2"] else 0
            trips[id] = [dep_counts, arr_counts]

            total_trips += dep_counts

        return trips, total_trips

    
    def calc_p_value_perm(self, metric):
        '''
        Returns the P-value using permutation tests.
        For a large number of times, it permutes the rows of the 
        produced trips and real trips and calculates metric on the 'new' data.
        It returns the proportion of times the permuted data produced better 
        results than the observed.
        '''
        shuffle_times = 10**4 - 1
        perm_results = []
        dist_observed = metric()

        all_trips = (self.produced + self.real)[:]
        dist_observed = metric()
        
        for i in range(shuffle_times):
            shuffled_indices = range(0, len(all_trips))
            random.shuffle(shuffled_indices)
            shuffled_indices_p = shuffled_indices[:len(self.produced)]
            shuffled_indices_r = shuffled_indices[len(self.produced):]
            
            new_produced = [all_trips[j] for j in shuffled_indices_p]
            new_real = [all_trips[j] for j in shuffled_indices_r]
            self.produced = new_produced
            self.real = new_real
            
            dist_new = metric()
            perm_results.append(dist_new)
            
        # number of results greater than observed
        gtobserved = sum([1 for res in perm_results if res >= dist_observed])

        return float(gtobserved + 1) / (shuffle_times + 1)

    def eval_man_dist(self):
        total_diff = 0
        total_real = 0

        if self.verbose:
            print "\nManhattan Distance Calculations ---->"
            print "\n\n\n%15s | %15s | %15s | %15s | %15s | %15s" %("station id",
                                                                    "produced dep", 
                                                                    "real dep",
                                                                    "produced arr",
                                                                    "real arr",
                                                                    "difference")
            
        total_departures = 0
        total_arrivals = 0

        for i in range(len(self.station_ids)):

            diff = abs(self.produced[i][0] - self.real[i][0]) + \
                   abs(self.produced[i][1] - self.real[i][1])

            if self.verbose:
                print "%15s | %15s | %15s | %15s | %15s | %15s" %(self.station_ids[i],
                                                                  self.produced[i][0],
                                                                  self.real[i][0],
                                                                  self.produced[i][1],
                                                                  self.real[i][1],
                                                                  diff)
                
            total_diff += diff
            total_real += max(sum(self.real[i]), sum(self.produced[i]))

        result = (1-(float(total_diff)/total_real))*100 if total_real > 0 else 100
        return result

    def eval_man_indiv_dist(self, get_arrivals):
        total_diff = 0
        total_real = 0

        if self.verbose:
            if get_arrivals:
                print "\nArrivals Manhattan Distance Calculations ---->"
            else:
                print "\nDepartures Manhattan Distance Calculations ---->"

            print "\n\n\n%15s | %15s | %15s | %15s" %("id", "produced", "real", "difference")

        for i in range(len(self.produced)):
            diff = abs(self.produced[i][get_arrivals] - self.real[i][get_arrivals])

            if self.verbose:
                print "%15s | %15s | %15s | %15s" \
                %(self.station_ids[i], self.produced[i][get_arrivals], self.real[i][get_arrivals], diff)

            total_diff += diff
            total_real += max(self.real[i][get_arrivals], self.produced[i][get_arrivals])

        result = (1-(float(total_diff)/total_real))*100 if total_real > 0 else 100
        return result

    def eval_eucl_dist(self):
        total_diff = 0
        total_real = 0
        
        if self.verbose:
            print "\nEuclidean Distance Calculations ---->"
            print "\n\n\n%15s | %15s | %15s | %15s | %15s | %15s" %("station id",
                                                                    "produced dep", 
                                                                    "real dep",
                                                                    "produced arr",
                                                                    "real arr",
                                                                    "difference")
        
        for i in range(len(self.produced)):
            diff = (self.produced[i][0] - self.real[i][0])**2 \
                   + (self.produced[i][1] - self.real[i][1])**2

            if self.verbose:
                print "%15s | %15s | %15s | %15s | %15s | %15s" %(self.station_ids[i], 
                                                                  self.produced[i][0],
                                                                  self.real[i][0],
                                                                  self.produced[i][1],
                                                                  self.real[i][1],
                                                                  diff)
            
            total_diff += diff
            total_real += max(self.real[i][0]**2 + self.real[i][1]**2,
                              self.produced[i][0]**2 + self.produced[i][1]**2)
            
        result = (1-(float(total_diff)/total_real))*100 if total_real > 0 else 100
        return result



def main():
    run_all = False
    
    if run_all:
        start_date = datetime.strptime("2011-01-01",
                                       '%Y-%m-%d')
        end_date = datetime.strptime("2013-06-30",
                                     '%Y-%m-%d')
        all_dates = []
        date_ranges = []
        for week in rrule.rrule(rrule.WEEKLY, dtstart=start_date, until=end_date):
            all_dates.append(week)
        for i in range(len(all_dates)-1):
            date_ranges.append((all_dates[i], all_dates[i+1]))

        man_accuracies = []
        eucl_accuracies = []

        outfile = open("results2.txt", "w")

        for (start, end) in date_ranges:
            re = RangeEvaluator(start, end, logic_options={'drop_stations':[31704]})
            man = re.eval_man_dist()
            eucl = re.eval_eucl_dist()
            start_date_string = datetime.strftime(start, '%Y-%m-%d')
            end_date_string = datetime.strftime(end, '%Y-%m-%d')
            outfile.write("--------------------------------------------\n")
            outfile.write("From: " + start_date_string+"\n")
            outfile.write("To: " + end_date_string+"\n")
            outfile.write("Accuracy based on Manhattan distance: %.2f %%\n" % (man))
            outfile.write("Accuracy based on Euclidean distance: %.2f %%\n" % (eucl))
            man_accuracies.append(man)
            eucl_accuracies.append(eucl)

        man_accuracies = np.array(man_accuracies)
        eucl_accuracies = np.array(eucl_accuracies)

        outfile.write("\n\nMean of Manhattan Accuracies: %.2f %%\n" % (np.mean(man_accuracies)))
        outfile.write("Standard Error of Manhattan Accuracies: %.2f %%\n" % (np.std(man_accuracies)))
        outfile.write("\n\nMean of Euclidean Accuracies: %.2f %%\n" % (np.mean(eucl_accuracies)))
        outfile.write("Standard Error of Euclidean Accuracies: %.2f %%\n" % (np.std(eucl_accuracies)))

        sys.exit()
        

    if len(sys.argv) == 1:
        start_date = datetime.strptime('2012-6-8',
                                       '%Y-%m-%d')
        end_date = datetime.strptime('2012-6-10',
                                     '%Y-%m-%d')
    elif len(sys.argv) == 3:
        start_date = datetime.strptime(sys.argv[1], 
                                       '%Y-%m-%d')
        end_date = datetime.strptime(sys.argv[2], 
                                     '%Y-%m-%d')
    else:
        sys.exit("You need a start date and an end date")

    re = RangeEvaluator(start_date, end_date, logic_options={'drop_stations':[31704]})
    re.verbose = False
    man = re.eval_man_dist()
    eucl = re.eval_eucl_dist()
    man_arr = re.eval_man_indiv_dist(True)
    man_dep = re.eval_man_indiv_dist(False)

    print "accuracy based on manhattan distance: ", man, "%"
    print "accuracy based on euclidean distance: ", eucl, "%"
    print "accuracy of arrivals by m-distance: ",man_arr, "%"
    print "accuracy of departures by m-distance: ",man_dep, "%"
    # print "p-value: ", re.calc_p_value_perm(re.eval_man_dist)

if __name__ == "__main__":
    main()
