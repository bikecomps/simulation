#! /usr/bin/env python

'''
    poissonLogic.py

    Questions we still have about distributions:
    - Do we have to specify standard deviation and whatever the poisson equivalent is? (Perhaps we use scipy's rvs function but I haven't figured it out yet.)
'''
from ..utils import Connector
from ..models import *

from scipy.stats import poisson
import numpy
import random
from simulationLogic import SimulationLogic
import datetime

class PoissonLogic(SimulationLogic):

    def __init__(self, session):
        SimulationLogic.__init__(self, session)

    def initialize(self, start_time):
        SimulationLogic.initialize(self, start_time)
        
        # Right now we're just saving the first closest station, 
        # easily modifiable to keep a list of closest stations
        self.nearest_stations = {}
        station_list = self.session.query(Station) 
        for station in station_list:
            nearest_distance = self.session.query(StationDistance)\
                    .filter(StationDistance.station1_id == station.id)\
                    .order_by(StationDistance.distance).first()
            self.nearest_stations[station.id] = nearest_distance

    def update(self, timestep):
        '''Moves the simulation forward one timestep from given time'''

        # We want to be able to cache off the distributions at each time step 
        # such that they're accessible from any part of the logic
        lambda_hour = self.time.hour
        lambda_day_of_week = self.time.weekday()

        self.lambda_distrs = self.get_lambdas(lambda_hour, lambda_day_of_week)

        # Technically we don't need to grab these every times but if we get more advanced
        # distributions presumably we would
        self.gaussian_distrs = self.get_gaussians()

        self.generate_new_trips(self.time)
        self.resolve_trips()

        # Increment after we run for the current timestep?
        self.time += timestep


    def generate_new_trips(self, start_time):
        # Note that Monday is day 0 and Sunday is day 6. Is this the same for models?
        station_count = 0
        for start_station_id in self.stations:
            station_count += 1
            for end_station_id in self.stations:
                lam = self.lambda_distrs.get((start_station_id, end_station_id), None)
                gauss = self.gaussian_distrs.get((start_station_id, end_station_id), None)

                # Else?
                if lam and gauss:
                    num_trips = self.get_num_trips(lam)
                    for i in range(num_trips):
                        # Starting time of the trip is randomly chosen within the Lambda's time range, which is hard-coded to be an hour.
                        added_time = datetime.timedelta(0, random.randint(0, 59), 0, 0, random.randint(0, 59), 0, 0)
                        trip_start_time = start_time + added_time
                        trip_duration = self.get_trip_duration(gauss)
                        trip_end_time = trip_start_time + trip_duration
                        new_trip = Trip(str(random.randint(1,500)), "Casual", "Produced", \
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


    def get_gaussians(self):
        """
        Caches gaussian distribution values into a dictionary.
        """
        gaussian_distr = self.session.query(GaussianDistr)

        distr_dict = {}
        for gauss in gaussian_distr:
            distr_dict[(gauss.start_station_id, gauss.end_station_id)] = gauss
        return distr_dict

    def get_lambdas(self, hour, day_of_week):
        """
        Caches lambdas into a dictionary for the given hour and day_of_week.
        """
        lambda_poisson = self.session.query(Lambda)\
                .filter(Lambda.hour == hour)\
                .filter(Lambda.day_of_week == day_of_week)
        # (station_id_1,  station_id_2) -> lambda
        distr_dict = {}

        for lam in lambda_poisson:
            distr_dict[(lam.start_station_id, lam.end_station_id)] = lam

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
        nearest_distance = self.session.query(StationDistance)\
                                    .filter(StationDistance.station1_id == depart_station_id)\
                                    .order_by(StationDistance.distance)[0]
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
