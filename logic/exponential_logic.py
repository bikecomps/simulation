#!/usr/bin/env python
'''
Jeff's Exponential Logic Idea
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
import bisect

class ExponentialLogic(SimulationLogic):

    def __init__(self, session):
        SimulationLogic.__init__(self, session)

    def initialize(self, start_time, end_time):
        SimulationLogic.initialize(self, start_time, end_time)

        self.exp_distrs = self.load_exp_lambdas(start_time, end_time)
        self.duration_distrs = self.load_gammas()
        self.dest_distrs = self.load_dest_distrs()

        # Retrieve StationDistance objects representing the five closest
        # stations for each stations.
        self.nearest_station_dists = {}
        station_list = self.session.query(data_model.Station) 
        for station in station_list:
            nearest_distances = self.session.query(data_model.StationDistance)\
                    .filter(data_model.StationDistance.station1_id == station.id)\
                    .order_by(data_model.StationDistance.distance)[:8]
            self.nearest_station_dists[station.id] = nearest_distances

        #TODO Generate initial trips for every station
        self.initialize_trips()

    def update(self, timestep):
        '''Moves the simulation forward one timestep from given time'''
        self.resolve_trips()

        # Increment after we run for the current timestep?
        self.time += timestep

    def initialize_trips(self):
        hour = self.start_time.hour
        day = self.start_time.day
        for s_id in self.stations.iterkeys():
            new_trip = self.generate_trip(s_id, self.start_time)
            self.pending_departures.put((new_trip.start_date, new_trip))

    def generate_trip(self, s_id, time):
        exp_l = self.exp_distrs[time.day][time.hour][s_id]
        #? Size parameter? 
        # Returns time till next event in seconds
        wait_time = numpy.random.exponential(1.0/exp_l.rate)
        trip_start_time = time + datetime.timedelta(seconds=wait_time)
        trip_duration = self.get_trip_duration(gamma)
        trip_end_time = trip_start_time + trip_duration

        #TODO create this function
        end_station_id = self.get_destination(s_id, time)

        #TODO Add new TripType 
        new_trip = data_model.Trip(str(random.randint(1,500)), 
            "Casual", 2, start_time, end_time, s_id, end_station_id)
        return new_trip

    def get_destination(self, s_id, time):
        '''
            Returns a destination station given dest_distrs
        '''
        vectors = self.dest_distrs[time.day][time.hour][s_id]
        cum_prob_vector = vectors[0]
        station_vector = vectors[1]

        # cum_prob_vector[-1] should be 1 No scaling needed as described here:
        # http://docs.python.org/3/library/random.html (very bottom of page)
        x = random.random()
        return station_vector[bisect.bisect(cum_prob_vector, x)]


    def load_gammas(self):
        '''
        Caches gaussian distribution variables into a dictionary.
        '''
        gamma_distr = self.session.query(data_model.Gamma)
        distr_dict = {}
        for gamma in gamma_distr:
            distr_dict[(gamma.start_station_id, gamma.end_station_id)] = gamma 
        return distr_dict

    def load_exp_lambdas(self, start_time, end_time):
        '''
        Caches exp lambdas into dictionary of day -> hour -> station_id -> exp lambda
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
            #lambda_poisson = self.session.query(data_model.Lambda) \
            #    .filter(data_model.Lambda.day_of_week == dow) \
            #    .filter(data_model.Lambda.hour.between(start_hour, end_hour))

#TODO Figure out how to actually load exp_lambdas
        
            for lam in lambda_poisson:
                distr_dict[lam.day_of_week][lam.hour][(lam.start_station_id, lam.end_station_id)] = lam
        return distr_dict

    def load_dest_distrs(self, start_time, end_time):
        '''
        Caches destination distributions into dictionary of day -> hour -> start_station_id -> [cumulative_distr, corresponding stations]

        '''
        distr_dict = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))


        # Inclusive
        #TODO figure out what to do if timespan > a week -> incline to say ignore it
        for day in rrule.rrule(rrule.DAILY, dtstart=start_time, until=end_time):
            dow = day.weekday()
            
            start_hour = start_time.hour if start_time.weekday() == dow else 0
            end_hour = end_time.hour if end_time.weekday() == dow else 24

            date_distrs = self.session.query(data_model.DestDistr) \
               .filter(data_model.DestDistr.day_of_week == dow) \
               .filter(data_model.DestDistr.hour.between(start_hour, end_hour))

            for distr in date_distrs:
                result = distr_dict[distr.day_of_week][distr.hour][distr.start_station_id]

                # Unencountered  day, hour, start_station_id -> Create the list of lists containing distribution probability values and corresponding end station ids.
                if len(result) == 0:
                    distr_dict[distr.day_of_week][distr.hour][distr.start_station_id] = [[distr.prob], [distr.station_id]]
                else:
                    result[0].append(distr.prob)
                    result[1].append(distr.station_id)

            # Change all of the probability vectors into cumulative probability vectors
            for day in date_distrs.itervalues():
                for hour in day.itervalues():
                    for s_id, vectors in hour.iteritems():
                        prob_vector = vectors[0]
                        cum_prob_vector = list(itertools.accumulate(prob_vector))
                        vectors[0] = cum_prob_vector

        return distr_dict

    def get_trip_duration(self, gamma):
        '''
        Samples from a gamma distribution and returns a timedelta representing
        a trip length
        '''
        trip_length = numpy.random.gamma(gamma.shape, gamma.scale)
        return datetime.timedelta(seconds=trip_length)

    def resolve_departure(self, trip):
        '''Decrement station count, put in pending_arrivals queue. If station is empty, put it in the disappointments list.'''
        departure_station_ID = trip.start_station_id

        if self.station_counts[departure_station_ID] == 0:
            new_disappointment = Disappointment(departure_station_ID, trip.start_date, trip_id=None)
            self.session.add(new_disappointment)
            self.disappointment_list.append(new_disappointment)
            self.resolve_sad_departure(trip)
        else:
            self.station_counts[departure_station_ID] -= 1
            self.pending_arrivals.put((trip.end_date, trip))
            new_trip = self.generate_trip(departure_station_ID, trip.start_date)
            self.pending_departures.put((new_trip.start_date, new_trip))

    def resolve_sad_departure(self, trip):
        '''
        Currently does nothing. Used to do this: changes trip.start_station_id to the id of the station nearest to it. Updates both trip.start_date and trip.end_date using get_trip_duration(), puts the updated trip into pending_departures. 
        '''
        pass

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
        
        gamma = self.duration_distrs.get((trip.end_station_id, nearest_station), None)
        if gamma:
            trip.end_station_id = nearest_station
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
    print durs
if __name__ == '__main__':

