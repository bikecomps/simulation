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

class AlPoissonLogic(SimulationLogic):

    def __init__(self, session):
        SimulationLogic.__init__(self, session)

    def initialize(self, start_time, end_time):
        SimulationLogic.initialize(self, start_time, end_time)
        self.lambda_distrs = self.load_lambdas(start_time, end_time)
        self.duration_distrs = self.load_gammas()
        self.dest_distrs = self.load_dest_distrs(start_time, end_time)

        # Retrieve StationDistance objects representing the five closest
        # stations for each stations.
        self.nearest_station_dists = {}
        station_list = self.session.query(data_model.Station) 
        for station in station_list:
            nearest_distances = self.session.query(data_model.StationDistance)\
                    .filter(data_model.StationDistance.station1_id == station.id)\
                    .order_by(data_model.StationDistance.distance)[:8]
            self.nearest_station_dists[station.id] = nearest_distances
        self.moving_bikes = 0


    def update(self, timestep):
        '''Moves the simulation forward one timestep from given time'''
        not_full = []
        not_empty = []
        full = []
        empty = [] 
        for s_id in self.station_counts:
            if s_id in self.empty_full_stations:
	        if self.station_counts[s_id] > 0 and self.empty_full_stations[s_id] == "empty":
                    not_empty.append(s_id)
                    del self.empty_full_stations[s_id]      
                elif self.station_counts[s_id] != self.stations[s_id].capacity:
		    not_full.append(s_id)
                    del self.empty_full_stations[s_id]
            else:
                if self.station_counts[s_id] == self.stations[s_id].capacity:
                    full.append(s_id)
                    self.empty_full_stations[s_id] = "full"
                if self.station_counts[s_id] == 0:
                    empty.append(s_id)
                    self.empty_full_stations[s_id] = "empty"

        self.generate_new_trips(self.time)
        self.resolve_trips()

        # Increment after we run for the current timestep?
        self.time += timestep

    def rebalance_stations(self, full, empty):
		
        for station_id in full:
            to_remove = self.stations[station_id].capacity/2
            self.station_counts[station_id] -= to_remove
            self.moving_bikes += to_remove

        while self.moving_bikes < len(empty):
            random_station = random.choice(self.station_counts.keys())
            if self.station_counts[random_station] > 1:
                self.station_counts[random_station] -= 1
                self.moving_bikes += 1
		
        if len(empty) > 0:
            bikes_per_station = self.moving_bikes / len(empty)
            for station_id in empty:
                self.station_counts[station_id] = bikes_per_station
                self.moving_bikes -= bikes_per_station

    def load_dest_distrs(self, start_time, end_time):
        '''
        Caches destination distributions into dictionary of day -> hour -> start_station_id -> [cumulative_distr, corresponding stations]
        # Change to a list of lists, faster, more space efficient
        '''
        distr_dict = [[{s_id:[] for s_id in self.stations.iterkeys()} for h in range(24)] for d in range(7)]


        # Inclusive
        #TODO figure out what to do if timespan > a week -> incline to say ignore it
        #TODO Bug: loading too much data at the moment, by a fair amount
        for day in rrule.rrule(rrule.DAILY, dtstart=start_time, until=end_time):
            dow = day.weekday()
            
            start_hour = start_time.hour if start_time.weekday() == dow else 0
            end_hour = end_time.hour if end_time.weekday() == dow else 24

            date_distrs = self.session.query(data_model.DestDistr) \
               .filter(data_model.DestDistr.day_of_week == dow) \
               .filter(data_model.DestDistr.hour.between(start_hour, end_hour)) \
               .filter(data_model.DestDistr.prob > 0).yield_per(10000)

            for distr in date_distrs:
                result = distr_dict[distr.day_of_week][distr.hour][distr.start_station_id]
                #if distr.start_station_id == 31101:
                #    print result

                # Unencountered  day, hour, start_station_id -> Create the list of lists containing distribution probability values and corresponding end station ids.
                if len(result) == 0:
                    distr_dict[distr.day_of_week][distr.hour][distr.start_station_id] = [[distr.prob], [distr.end_station_id]]
                else:
                    result[0].append(distr.prob)
                    result[1].append(distr.end_station_id)

            print "\t\tStarting reductions"
            # Change all of the probability vectors into cumulative probability vectors
            for hour in distr_dict[dow]:
                for s_id, vectors in hour.iteritems():
                    # We have data for choosing destination vector
                    if len(vectors) == 2:
                        prob_vector = vectors[0]
                        # thanks to http://stackoverflow.com/questions/14132545/itertools-accumulate-versus-functools-reduce
                        # for basic accumulator code
                        cum_prob_vector = reduce(lambda a, x: a + [a[-1] + x], prob_vector[1:], [prob_vector[0]])
                        vectors[0] = cum_prob_vector
        return distr_dict


    def get_destination(self, s_id, time):
        '''
            Returns a destination station given dest_distrs
        '''
        #print time.day, time.hour, s_id
        vectors = self.dest_distrs[time.weekday()][time.hour][s_id]
        if len(vectors) > 0:
            cum_prob_vector = vectors[0]
            station_vector = vectors[1]

            # cum_prob_vector[-1] should be 1 No scaling needed as described here:
            # http://docs.python.org/3/library/random.html (very bottom of page)
            x = random.random()
        
            return station_vector[bisect.bisect(cum_prob_vector, x)]
        else:
            print "Error getting destination: Day",time.day,"hour",time.hour,"s_id",s_id
            # Send it to one of 273 randomly
            return random.choice(self.stations.keys())

    def generate_new_trips(self, start_time):
        for s_id in self.station_counts:
            lam = self.get_lambda(start_time.year, start_time.month,
                                  start_time.weekday(), start_time.hour,
                                  start_station_id, end_station_id)
            if lam:
                num_trips = self.get_num_trips(lam)
                for i in xrange(num_trips):
                    e_id = self.get_destination(s_id)
                    gamma = self.duration_distrs.get((s_id, e_id), None)
                    if gamma:
                        added_time = datetime.timedelta(seconds=random.randint(3600))
                        trip_start_time = start_time + added_time
                        trip_duration = self.get_trip_duration(gamma)
                        trip_end_time = trip_start_time + trip_duration
                        new_trip = data_model.Trip(str(random.randint(1,500)), 
                                                  "Casual", 2, 
                                                  trip_start_time, trip_end_time,
                                                  s_id, e_id)
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

    def get_lambda(self, year, month, day, hour, start_station, end_station):
        '''
        If there is a lambda, return it. Otherwise return None as we only 
        load non-zero lambdas from the database for performance reasons.
        '''
        return self.lambda_distrs.get(year, {}).get(month, {}).get(day < 5, {}).get(hour, {}).get((start_station, end_station), None)

    def load_lambdas(self, start_time, end_time):
        '''
        Caches lambdas into dictionary of day -> hour -> (start_id, end_id) -> lambda
        Note: DB only has values > 0.
        '''
        # kind of gross but makes for easy housekeeping
        distr_dict = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(float)))))

        num_added = 0
        # Inclusive
        for day in rrule.rrule(rrule.DAILY, dtstart=start_time, until=end_time):
            dow = day.weekday()
            
            start_hour = start_time.hour if start_time.weekday() == dow else 0
            end_hour = end_time.hour if end_time.weekday() == dow else 24

            year = start_time.year
            month = start_time.month
            is_week_day = dow < 5

            # For now we're only loading in lambdas that have non-zero values. 
            # We'll assume zero value if it's not in the dictionary
            lambda_poisson = self.session.query(data_model.Lambda) \
                .filter(data_model.Lambda.is_week_day == is_week_day) \
                .filter(data_model.Lambda.year ==  year) \
                .filter(data_model.Lambda.month == month) \
                .filter(data_model.Lambda.hour.between(start_hour, end_hour))
        
            for lam in lambda_poisson:
                distr_dict[year][month][lam.is_week_day][lam.hour][(lam.start_station_id, lam.end_station_id)] = lam
                num_added += 1

        print "Loaded %s lambdas" % num_added
        return distr_dict

    def get_trip_duration(self, gamma):
        '''
        Samples from a gamma distribution and returns a timedelta representing
        a trip length
        '''
        #TODO Fix this
        if gamma.shape <= 0 or gamma.scale <= 0:
            return datetime.timedelta(seconds=0)
        trip_length = numpy.random.gamma(gamma.shape, gamma.scale)
        return datetime.timedelta(seconds=trip_length)

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
    print durs
if __name__ == '__main__':
    main()
