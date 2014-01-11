#!/usr/bin/env python
'''
    poissonLogic.py

    Questions we still have about distributions:
    - Do we have to specify standard deviation and whatever the poisson equivalent is? (Perhaps we use scipy's rvs function but I haven't figured it out yet.)
'''
from utils import Connector
from models import *
from scipy.stats import poisson
import numpy
import random
from simulationLogic import SimulationLogic
import datetime
from dateutil import rrule
from collections import defaultdict

class PoissonLogic(SimulationLogic):

    def __init__(self, session):
        SimulationLogic.__init__(self, session)

    def initialize(self, start_time, end_time):
        SimulationLogic.initialize(self, start_time, end_time)

        self.lambda_distrs = self.load_lambdas(start_time, end_time)
        self.gaussian_distrs = self.load_gaussians()
        

        # Right now we're just saving the first closest station, 
        # easily modifiable to keep a list of closest stations
        self.nearest_stations = {}
        station_list = self.session.query(data_model.Station) 
        for station in station_list:
            nearest_distance = self.session.query(data_model.StationDistance)\
                    .filter(data_model.StationDistance.station1_id == station.id)\
                    .order_by(data_model.StationDistance.distance).first()
            self.nearest_stations[station.id] = nearest_distance


    def update(self, timestep):
        '''Moves the simulation forward one timestep from given time'''

        # We want to be able to cache off the distributions at each time step 
        # such that they're accessible from any part of the logic
        lambda_hour = self.time.hour
        lambda_day_of_week = self.time.weekday()

        # Technically we don't need to grab these every times but if we get more advanced
        # distributions presumably we would
        self.gaussian_distrs = self.load_gaussians()

        self.generate_new_trips(self.time)
        self.resolve_trips()

        # Increment after we run for the current timestep?
        self.time += timestep

    def generate_new_trips(self, start_time):
        # Note that Monday is day 0 and Sunday is day 6. Is this the same for data_model?
        station_count = 0
        for start_station_id in self.stations:
            station_count += 1
            for end_station_id in self.stations:
                lam = self.get_lambda(start_time.weekday(), start_time.hour,\
                         start_station_id, end_station_id)
                gauss = self.gaussian_distrs.get((start_station_id, end_station_id), None)

                # Else?
                # Check for invalid queries
                if lam and gauss:
                    num_trips = self.get_num_trips(lam)
                    for i in range(num_trips):
                        # Starting time of the trip is randomly chosen within the Lambda's time range, which is hard-coded to be an hour.
                        added_time = datetime.timedelta(0, random.randint(0, 59), 0, 0, random.randint(0, 59), 0, 0)
                        trip_start_time = start_time + added_time
                        trip_duration = self.get_trip_duration(gauss)
                        trip_end_time = trip_start_time + trip_duration
                        new_trip = data_model.Trip(str(random.randint(1,500)), "Casual", "Produced", \
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
            #TODO: Should we do something here?
            num_trips = -1
        return int(num_trips)


    def load_gaussians(self):
        """
        Caches gaussian distribution values into a dictionary.
        """
        gaussian_distr = self.session.query(data_model.GaussianDistr)

        distr_dict = {}
        for gauss in gaussian_distr:
            distr_dict[(gauss.start_station_id, gauss.end_station_id)] = gauss
        return distr_dict

    def old_load_lambdas(self, hour, day_of_week):
        """
        Caches lambdas into a dictionary for the given hour and day_of_week.
        """
        lambda_poisson = self.session.query(data_model.Lambda)\
                .filter(data_model.Lambda.hour == hour)\
                .filter(data_model.Lambda.day_of_week == day_of_week)
        # (station_id_1,  station_id_2) -> lambda
        distr_dict = {}

        for lam in lambda_poisson:
            distr_dict[(lam.start_station_id, lam.end_station_id)] = lam

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

    def get_trip_duration(self, gauss):
        '''
        Samples from a gaussian distribution and returns a timedelta
        representing a trip length.
        '''
        trip_length = random.gauss(gauss.mean, gauss.std)
        return datetime.timedelta(seconds=trip_length)


    '''
    ISSUE: If there is a disappointment, the trip is rerouted to the nearest station. That sounds good in theory but what happens if two stations are full and they happen to be the closest stations to each other? Infinite loops! We need to figure out a better system for what happens here clearly.

    Right now... I'm going to do nothing
    '''

    def resolve_sad_arrival(self, trip):
        '''
        Changes trip.end_station_id to the id of the station nearest to it and updates trip.end_date accordingly. Puts the updated trip into pending_arrivals.
        '''
        nearest_station = self.nearest_stations.get(trip.end_station_id)
        gauss = self.gaussian_distrs.get((trip.end_station_id, nearest_station.station2_id), None)
        if gauss:
            trip_duration = self.get_trip_duration(gauss)
            # Do we really want to do this? Do we not want to convert this into 2 trips?
            trip.end_date += trip_duration
            return
            self.pending_arrivals.put((trip.end_date, trip))


    def resolve_sad_departure(self, trip):
        '''
        Currently changes trip.start_station_id to the id of the station nearest to it. Updates both trip.start_date and trip.end_date using get_trip_duration(), puts the updated trip into pending_departures. 
        '''
        """
        depart_station_id = trip.start_station_id
        # SELECT station2_id from station_distances WHERE station1_id=depart_station_id order by distance limit 1;
        # returns a StationDistance object in which station2_id is the station nearest to arrive_station
        nearest_distance = self.session.query(data_model.StationDistance)\
                                    .filter(data_model.StationDistance.station1_id == depart_station_id)\
                                    .order_by(data_model.StationDistance.distance)[0]
        nearest_station_id = nearest_distance.station2_id
        trip.start_station_id = nearest_station_id
        """

        nearest_station = self.nearest_stations.get(trip.start_station_id)
        gauss = self.gaussian_distrs.get((trip.end_station_id, nearest_station.station2_id), None)
        if gauss:
            trip_duration = self.get_trip_duration(gauss)
            # Do we really want to do this? Do we not want to convert this into 2 trips?
            trip.end_date += trip_duration
            return
            self.pending_departures.put((trip.start_date, trip))

    def clean_up(self):
        pass

def main():
    connector = Connector()
    session = connector.getDBSession()
    p = PoissonLogic(session)
    print p.get_trip_duration(31100, 31101)

if __name__ == '__main__':
    main()
