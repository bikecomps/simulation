#! /usr/bin/env python
"""
This 'evaluator' is used to print either the euclidean or manhattan
distance between the vector of produced trips and the vector of
real trips.
"""

from logic import PoissonLogic, Simulator
from utils import Connector
from models import Trip, Station

from datetime import datetime

import sys

class RangeEvaluator:
    def __init__(self, start_date, end_date):
        self.start_date = start_date
        self.end_date = end_date

        # by default, evaluator is not verbose
        self.verbose = False

        c = Connector()
        self.session = c.getDBSession()
        self.engine = c.getDBEngine()

        # store produced and real trips in dictionaries
        # station id -> [number of departures, number of arrivals]
        self.produced = self.get_produced_trips()
        self.real = self.get_real_trips()

    def get_produced_trips(self):
        logic = PoissonLogic(self.session)
        simulator = Simulator(logic)
        results = simulator.run(self.start_date, self.end_date)
        
        trips = {}
        for trip in results['trips']:
            trips.setdefault(trip.start_station_id, [0, 0])
            trips.setdefault(trip.end_station_id, [0, 0])

            trips[trip.start_station_id][0] += 1
            trips[trip.end_station_id][1] += 1

        return trips
        
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
        for row in results:
            id = row["id1"] if row["id1"] else row["id2"]
            dep_counts = row["c1"] if row["c1"] else 0
            arr_counts = row["c2"] if row["c2"] else 0
            trips[id] = [dep_counts, arr_counts]
        
        return trips

    def eval_man_dist(self):
        total_diff = 0
        total_real = 0

        if self.verbose:
            print "%15s | %15s | %15s | %15s" %("id", "name", "produced", "real")

        for k in self.produced:
            diff = abs(self.produced[k][0] - self.real[k][0]) + \
                   abs(self.produced[k][1] - self.real[k][1])
            if self.verbose:
                print "%15s | %15s | %15s | %15s" \
                %(k, self.produced[k], self.real[k], diff)

            total_diff += diff
            total_real += max(sum(self.real[k]), sum(self.produced[k]))

        return (1-(float(total_diff)/total_real))*100

    def eval_eucl_dist(self):
        total_diff = 0
        total_real = 0
        
        if self.verbose:
            print "%15s | %15s | %15s | %15s" %("id", "name", "produced", "real")
        
        for k in self.produced:
            diff = (self.produced[k][0] - self.real[k][0])**2
            +(self.produced[k][1] - self.real[k][1])**2

            if self.verbose:
                print "%15s | %15s | %15s | %15s" \
                %(k, self.produced[k], self.real[k], diff)
            
            total_diff += diff
            total_real += max(self.real[k][0]**2 + self.real[k][1]**2,
                              self.produced[k][0]**2 + self.produced[k][1]**2)
            
        return (1-(float(total_diff)/total_real))*100

def main():
    if len(sys.argv) == 1:
        start_date = datetime.strptime('2012-1-1',
                                       '%Y-%m-%d')
        end_date = datetime.strptime('2012-1-2',
                                     '%Y-%m-%d')
    elif len(sys.argv) == 3:
        start_date = datetime.strptime(sys.argv[1], 
                                       '%Y-%m-%d')
        end_date = datetime.strptime(sys.argv[2], 
                                     '%Y-%m-%d')
    else:
        sys.exit("You need a start date and an end date")

    re = RangeEvaluator(start_date, end_date)
    re.verbose = True

    man = re.eval_man_dist()
    eucl = re.eval_eucl_dist()
    print "accuracy based on manhattan distance: ", man, "%"
    print "accuracy based on euclidean distance: ", eucl, "%"

if __name__ == "__main__":
    main()
