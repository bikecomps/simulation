#!/usr/bin/env python
'''
    poisson_logic.py

    Questions we still have about distributions:
    - Do we have to specify standard deviation and whatever the poisson equivalent is? (Perhaps we use scipy's rvs function but I haven't figured it out yet.)
'''
from utils import Connector
from models import *
from scipy.stats import poisson
import numpy
import random
from simulation_logic import SimulationLogic
import datetime
from dateutil import rrule
from collections import defaultdict

class PoissonLogic(SimulationLogic):

    def __init__(self, session):
        SimulationLogic.__init__(self, session)

    def initialize(self, start_time, end_time):
        SimulationLogic.initialize(self, start_time, end_time)

        self.lambda_distrs = self.load_lambdas(start_time, end_time)
        #self.gaussian_distrs = self.load_gaussians()
        self.duration_distrs = self.load_gammas()
        

        # Retrieve StationDistance objects representing the five closest
        # stations for each stations.
        self.nearest_station_dists = {}
        station_list = self.session.query(data_model.Station) 
        for station in station_list:
            nearest_distances = self.session.query(data_model.StationDistance)\
                    .filter(data_model.StationDistance.station1_id == station.id)\
                    .order_by(data_model.StationDistance.distance)[:5]
            self.nearest_station_dists[station.id] = nearest_distances


    def update(self, timestep):
        '''Moves the simulation forward one timestep from given time'''
        self.generate_new_trips(self.time)
        self.resolve_trips()

        # Increment after we run for the current timestep?
        self.time += timestep


    def generate_new_trips(self, start_time):
        # Note that Monday is day 0 and Sunday is day 6. Is this the same for data_model?
        station_count = 0
        for start_station_id in self.station_counts:
            station_count += 1
            for end_station_id in self.station_counts:
                lam = self.get_lambda(start_time.weekday(), start_time.hour,\
                         start_station_id, end_station_id)
                #gauss = self.gaussian_distrs.get((start_station_id, end_station_id), None)
                gamma = self.duration_distrs.get((start_station_id, end_station_id), None)
                # Check for invalid queries
                # print lam, gauss
                if lam and gamma:
                    num_trips = self.get_num_trips(lam)
                    for i in range(num_trips):
                        # Starting time of the trip is randomly chosen within the Lambda's time range, which is hard-coded to be an hour.
                        added_time = datetime.timedelta(0, random.randint(0, 59), 0, 0, random.randint(0, 59), 0, 0)
                        trip_start_time = start_time + added_time
                        #trip_duration = self.get_trip_duration(gauss)
                        trip_duration = self.get_trip_duration(gamma)
                        trip_end_time = trip_start_time + trip_duration
                        new_trip = data_model.Trip(str(random.randint(1,500)), "Casual", 2, \
                                trip_start_time, trip_end_time, start_station_id, end_station_id)
                        self.pending_departures.put((start_time, new_trip))

                

    def get_num_trips(self, lam):
        """
        Samples a poisson distribution with the given lambda and returns the number
        of trips produced from the dist. Returns -1 if lambda = 0 -> undefined function.
        """
        probability = random.random()
        while probability == 0:
            probability = random.random()
        num_trips = poisson.ppf(probability, lam.value)
        if numpy.isnan(num_trips):
            num_trips = -1
        return int(round(num_trips))


    def load_gaussians(self):
        """
        Caches gaussian distribution values into a dictionary.
        """
        gaussian_distr = self.session.query(data_model.GaussianDistr)

        distr_dict = {}
        for gauss in gaussian_distr:
            distr_dict[(gauss.start_station_id, gauss.end_station_id)] = gauss
        return distr_dict

    def load_gammas(self):
        '''
        Caches gaussian distribution variables into a dictionary.
        '''
        gamma_distr = self.session.query(data_model.Gamma)
        distr_dict = {}
        for gamma in gamma_distr:
            distr_dict[(gamma.start_station_id, gamma.end_station_id)] = gamma 
        return distr_dict

    def get_lambda(self, day, hour, start_station, end_station):
        '''
        If there is a lambda, return it. Otherwise return None as we only 
        load non-zero lambdas from the database for performance reasons.
        '''
        return self.lambda_distrs.get(day, {}).get(hour, {}).get((start_station, end_station), None)

    def load_lambdas(self, start_time, end_time):
        '''
        Caches lambdas into dictionary of day -> hour -> (start_id, end_id) -> lambda
        '''

        # kind of gross but makes for easy housekeeping
        distr_dict = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))

        # Inclusive
        for day in rrule.rrule(rrule.DAILY, dtstart=start_time, until=end_time):
            dow = day.weekday()
            
            start_hour = start_time.hour if start_time.weekday() == dow else 0
            end_hour = end_time.hour if end_time.weekday() == dow else 24

            # For now we're only loading in lambdas that have non-zero values. 
            # We'll assume zero value if it's not in the dictionary
            lambda_poisson = self.session.query(data_model.Lambda)\
                    .filter(data_model.Lambda.day_of_week == dow)\
                    .filter(data_model.Lambda.hour.between(start_hour, end_hour))\
                    .filter(data_model.Lambda.value > 0)
        
            for lam in lambda_poisson:
                distr_dict[lam.day_of_week][lam.hour][(lam.start_station_id, lam.end_station_id)] = lam
        return distr_dict

    def old_get_trip_duration(self, gauss):
        '''
        Samples from a gaussian distribution and returns a timedelta
        representing a trip length.
        '''
        trip_length = random.gauss(gauss.mean, gauss.std)
        return datetime.timedelta(seconds=trip_length)

    def get_trip_duration(self, gamma):
        '''
        Samples from a gamma distribution and returns a timedelta representing
        a trip length
        '''
        trip_length = numpy.random.gamma(gamma.shape, gamma.scale)
        return datetime.timedelta(seconds=trip_length)

    def resolve_sad_departure(self, trip):
        '''
        Currently does nothing. Used to do this: changes trip.start_station_id to the id of the station nearest to it. Updates both trip.start_date and trip.end_date using get_trip_duration(), puts the updated trip into pending_departures. 
        '''
        pass


    '''
    ISSUE: If there is a disappointment, the trip is rerouted to the nearest station. That sounds good in theory but what happens if two stations are full and they happen to be the closest stations to each other? Potentially resolved...

    '''
    def resolve_sad_arrival(self, trip):
        '''
        Changes trip.end_station_id to the id of the station nearest to it and updates trip.end_date accordingly. Puts the updated trip into pending_arrivals.
        '''
        station_list_index = 0
        nearest_station = self.nearest_station_dists.get(trip.end_station_id)[station_list_index].station2_id
        visited_stations = [disappointment.station_id for disappointment in trip.disappointments]
        while nearest_station in visited_stations:
            station_list_index+=1
            nearest_station = self.nearest_station_dists.get(trip.end_station_id)[station_list_index].station2_id
        
        #gauss = self.gaussian_distrs.get((trip.end_station_id, nearest_station), None)
        gamma = self.duration_distrs.get((trip.end_station_id, nearest_station), None)
        #if gauss:
        if gamma:
            trip.end_station_id = nearest_station
            #trip_duration = self.get_trip_duration(gauss)
            trip_duration = self.get_trip_duration(gamma)
            trip.end_date += trip_duration
            self.pending_arrivals.put((trip.end_date, trip))


    def clean_up(self):
        pass

def main():
    connector = Connector()
    session = connector.getDBSession()
    p = PoissonLogic(session)
    print p.get_trip_duration(31100, 31101)

if __name__ == '__main__':
    main()
