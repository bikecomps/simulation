# System modules
import csv
import datetime
import sys

# Our modules
from simulationLogic import SimulationLogic
from poissonLogic import PoissonLogic
from utility import Connector

class Simulator:
    def __init__(self, sim_logic):
        self.sim_logic = sim_logic

    def run(self, start_time, end_time, timestep=datetime.timedelta(seconds=3600)):
        self.sim_logic.initialize(start_time)

        cur_time = start_time
        #for time in range(start_time, end_time, timestep):
        while cur_time < end_time:
            self.sim_logic.update(timestep)
            cur_time += timestep

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
            writer = csv.csvwriter(f)
            for line in results:
                writer.write(line.to_csv()) 

def print_usage():
    print "Simulator Usage: python simulator.py <name of logic> <start_date> <end_date>"

def main():
    logic_options = {
        "SimulationLogic" : SimulationLogic,
        "PoissonLogic" : PoissonLogic
    }

    if len(sys.argv) < 4 or sys.argv[1] not in logic_options:
        print_usage()
        return
   
    raw_start_date = sys.argv[2]
    raw_end_date = sys.argv[3]
    
    start_date = datetime.datetime.strptime(raw_start_date, '%Y-%m-%d')
    end_date = datetime.datetime.strptime(raw_end_date, '%Y-%m-%d')

    session = Connector().getDBSession()
    logic = logic_options[sys.argv[1]](session)
    simulator = Simulator(logic) 
    results = simulator.run(start_date, end_date)
    simulator.write_out(results, file_name)
    

if __name__ == '__main__':
    main()
