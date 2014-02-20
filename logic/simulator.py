#!/usr/bin/env python

# System modules
import csv
import datetime
import sys
import random
random.seed(23526)

# Our modules
from models import *
from simulation_logic import SimulationLogic
from poisson_logic import PoissonLogic
from exponential_logic import ExponentialLogic
from alt_poisson_logic import AltPoissonLogic
from utils import Connector

import pickle

class Simulator:
    def __init__(self, sim_logic):
        self.sim_logic = sim_logic
        self.session = sim_logic.getDBSession()

    def run(self, start_time, end_time, 
            timestep=datetime.timedelta(seconds=3600),
            logic_options={}):
        '''
        logic_options must have keywords EXACTLY the sim_logic's named params
        '''

        self.sim_logic.initialize(start_time, end_time, **logic_options)

        cur_time = start_time
        print "cur time:", cur_time, "start time:", start_time, "end time:", end_time
        progress_buffer = {}
        progress_buffer["total_steps"] = (end_time - start_time).total_seconds()/timestep.seconds
        progress_buffer["done_steps"] = 0
        progress_buffer["current_time"] = start_time

        nfile = open("progress_buffer.dat", "w")
        pickle.dump(progress_buffer, nfile)       
        nfile.close()

        while cur_time < end_time:
            self.sim_logic.update(timestep)
            cur_time += timestep
            print "Finished time step ", cur_time
            
            progress_buffer["done_steps"] += 1
            progress_buffer["current_time"] = cur_time

            nfile = open("progress_buffer.dat", "w")
            pickle.dump(progress_buffer, nfile)       
            nfile.close()

        results = self.sim_logic.flush()
        self.sim_logic.clean_up()
        return results
    
    # I think I'd prefer to write out the results into the DB rather
    # than create a bunch of CSVs.
    def write_out(self, results, file_name):
        '''
        Takes in a list of trip objects and writes them out to a csv file
        '''
        with open(file_name, 'w') as f:
            f.write(Trip.csv_header() + "\n")
            for line in results['trips']:
                f.write(line.to_csv()+"\n")

    def save_to_db(self, trips, disappointments):
        '''
        Saves produced trips and associated disappointments to the db.
        '''
        trip_type = TripType('Produced')
        self.session.add(trip_type)
        for trip in trips:
            trip.trip_type = trip_type
            self.session.add(trip)
        for d in disappointments:
            self.session.add(d)
        self.session.commit() 
        self.session.flush()
        # self.session.commit() 

    # Return string to write to console, std out
    def write_stdout(self, results):
        return "\n".join([line.to_csv() for line in results])

def print_usage():
    print "Simulator Usage: python simulator.py <name of logic> <start_date> <end_date> <output file>"

def main():
    logic_options = {
        "SimulationLogic" : SimulationLogic,
        "PoissonLogic" : PoissonLogic,
        "ExponentialLogic" : ExponentialLogic
    }
    
    # For testing
    if len(sys.argv) == 1:
        # defaults
        raw_start_date = "2012-6-2 00:00:00"
        raw_end_date = "2012-6-3 00:00:00"
        file_name = "/tmp/test.csv"
        #logic = ExponentialLogic
        #logic = AltPoissonLogic
        logic = PoissonLogic
        start_date = datetime.datetime.strptime(raw_start_date, '%Y-%m-%d %H:%M:%S')
        end_date = datetime.datetime.strptime(raw_end_date, '%Y-%m-%d %H:%M:%S')
    else:
        if len(sys.argv) < 5 or sys.argv[1] not in logic_options:
            print_usage()
            return
        elif len(sys.argv) == 7:
            raw_start_date = sys.argv[2] + " " + sys.argv[3]
            raw_end_date = sys.argv[4] + " " + sys.argv[5]
            start_date = datetime.datetime.strptime(raw_start_date, '%Y-%m-%d %H:%M:%S')
            end_date = datetime.datetime.strptime(raw_end_date, '%Y-%m-%d %H:%M:%S')
            file_name = sys.argv[6]
        elif len(sys.argv) == 5:
            raw_start_date = sys.argv[2]
            raw_end_date = sys.argv[3]
            start_date = datetime.datetime.strptime(raw_start_date, '%Y-%m-%d')
            end_date = datetime.datetime.strptime(raw_end_date, '%Y-%m-%d') 
            file_name = sys.argv[4]
        else:
            print_usage()
            return 
    
        logic = logic_options[sys.argv[1]]
    
    print start_date,"-",end_date
    session = Connector().getDBSession()
    logic = logic(session)
    simulator = Simulator(logic) 
    print start_date, end_date
    logic_options = {'station_caps':{31237:5}, 'drop_stations':[31704,31000,31001,31002],
                     'rebalancing_time':datetime.timedelta(seconds=3600)}
    results = simulator.run(start_date, end_date, logic_options=logic_options)
    print "trips:", len(results['trips'])
    ds = results['disappointments']
    print "disappointments:", len(ds)
    num_ds = len([x for x in ds if x.trip == None])
    print "Empty diss", num_ds
    print "Full diss", len(ds) - num_ds
    print "Arrival dis stations:"
    print results['arr_dis_stations']
    print "Departure dis stations:"
    print results['dep_dis_stations']
    
    # simulator.write_out(results, file_name)
    # simulator.save_to_db(results['trips'])
    #simulator.write_out(results, file_name)
    #simulator.save_to_db(results['trips'])
    hours = [[0]*24 for d in range(7)]
    for t in results['trips']:
        hours[t.start_date.weekday()][t.start_date.hour] += 1

    # print "Times?"
    # for d in range(7):
    #    for i in range(24):
    #        print d,i,": ",hours[d][i]

    
    """
    stations = {}
    for t in results['trips']:
        if t.start_station_id in stations:
            stations[t.start_station_id] += 1
        else:
            stations[t.start_station_id] = 1

    print "Stations?"
    print len(stations.keys())
    for s_id, count in stations.iteritems():
        print s_id,count
    """

    session.close()
    

if __name__ == '__main__':
    main()
