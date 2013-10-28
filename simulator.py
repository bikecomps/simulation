import simulationLogic
import csv

class Simulator:
    def __init__(self, sim_logic):
        self.sim_logic = sim_logic

    # Still need to make timestep a datetime objects rather than
    # ints. They lose a lot of meaning when just integers.
    def run(self, start_time, end_time, timestep=1):
        self.sim_logic.initialize(start_time)

        for time in range(start_time, end_time, timestep):
            self.sim_logic.update(timestep)

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

def main():
    simulator = Simulator(simulationLogic.SimulationLogic()) 
    results = simulator.run(start_time, end_time)
    simulator.write_out(results, file_name)
    

if __name__ == '__main__':
    main()
