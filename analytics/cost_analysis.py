from logic import PoissonLogic, Simulator
from utils import Connector

import datetime as dt

# In dollars - these are made up
REBALANCE_COST = .03
BIKE_COST = .001
TRIP_REVENUE = .05

def calculate_cost(sim_results):
    num_bikes = sim_results['total_num_bikes']
    num_rebalances = sim_results['total_rebalances']
    num_trips = len(sim_results['trips'])
    num_dep_diss = len([d for d in sim_results['disappointments'] if not d.trip_id])
    

    bike_cost = num_bikes * BIKE_COST
    rebalance_cost = num_rebalances * REBALANCE_COST
    trips_revenue = num_trips * TRIP_REVENUE
    missed_revenue = num_dep_diss * TRIP_REVENUE

    return {'gross_rev':trips_revenue,
            'gross_cost':bike_cost + rebalance_cost,
            'missed_rev':missed_revenue}


def optimize_num_bikes(start_d, end_d, step_factor=.5, iters=10):
    '''
    iters: the number of times which to run the optimizer.
    step_factor: the max percentage by which to change the number of bikes at
            any given step.
    '''
    session = Connector().getDBSession()
    logic = PoissonLogic(session)
    simulator = Simulator(logic)

    # Get a baseline using default method of getting number of bikes
    run_options = {'bike_total':None}
    sim_results = simulator.run(start_d, end_d, 
                                logic_options=run_options)
    best_num_bikes = sim_results['total_num_bikes']
    costs = calculate_cost(sim_results)

    best_profit = costs['gross_rev'] - costs['gross_cost']
    best_costs = costs
    best_run_options = run_options
    # Small hack to get it working
    best_run_options['bike_total'] = best_num_bikes
    best_sim_data = sim_results

    print "Starting point:"
    print "Profit",best_profit
    print "Num bikes",best_num_bikes
    for i in xrange(iters):
        best_num_bikes = best_run_options['bike_total']

        # We should figure make it so that we don't have to rebuild simulator 
        # every time this isn't so annoying

        # Try above
        logic = PoissonLogic(session)
        simulator = Simulator(logic)
        up_num_bikes =  best_num_bikes * (1. + step_factor) 
        up_run_options = {'bike_total':up_num_bikes}
        up_sim_results = simulator.run(start_d, end_d,
                                    logic_options=up_run_options)
        up_costs = calculate_cost(up_sim_results)
        up_sim_profit = up_costs['gross_rev'] - up_costs['gross_cost']
        print "Above",up_num_bikes, up_sim_profit

        # Try lower
        logic = PoissonLogic(session)
        simulator = Simulator(logic)
        down_num_bikes =  best_num_bikes * (1. - step_factor) 
        down_run_options = {'bike_total':down_num_bikes}
        down_sim_results = simulator.run(start_d, end_d,
                                    logic_options=down_run_options)
        down_costs = calculate_cost(down_sim_results)
        down_sim_profit = down_costs['gross_rev'] - down_costs['gross_cost']
        print "Down",down_num_bikes, down_sim_profit
        
        # "Recurse" on the better profit"
        if up_sim_profit > down_sim_profit and up_sim_profit > best_profit:
            print "Better up! Recursing on",up_run_options['bike_total']
            best_profit = up_sim_profit
            best_costs = up_costs
            best_run_options = up_run_options
            best_sim_data = up_sim_results
        elif down_sim_profit > up_sim_profit and down_sim_profit > best_profit:
            print "Better Down! Recursing on",down_run_options['bike_total']
            best_profit = down_sim_profit
            best_costs = down_costs
            best_sim_data = down_sim_results
            best_run_options = down_run_options
        # Wasn't able to increase profits, try again with a smaller step (may have over stepped)
        else:
            print "Nothing better, try again"
            step_factor *= .5
    print "-"*30,"Best","-"*30
    print "Profit:",best_profit
    print "Run options:",best_run_options
    print "Costs:",best_costs
    print "Sim data:",

def main():
    raw_start_date = '2012-6-2 00:00:00'
    raw_end_date = '2012-6-3 00:00:00'
    start_date = dt.datetime.strptime(raw_start_date, '%Y-%m-%d %H:%M:%S')
    end_date = dt.datetime.strptime(raw_end_date, '%Y-%m-%d %H:%M:%S')
    optimize_num_bikes(start_date, end_date, iters=3)
    return

    session = Connector().getDBSession()
    logic = PoissonLogic(session)
    simulator = Simulator(logic)
    sim_results = simulator.run(start_date, end_date)

    print calculate_cost(sim_results)
    session.close()

if __name__ == '__main__':
    main()
