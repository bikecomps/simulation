#!/usr/bin/env python
'''
    poisson_logic.py

    Questions we still have about distributions:
    - Do we have to specify standard deviation and whatever the poisson equivalent is? (Perhaps we use scipy's rvs function but I haven't figured it out yet.)
'''
from utils import Connector
import bisect
from models import *
from scipy.stats import poisson
import numpy
import random
from simulation_logic import SimulationLogic
import datetime
from dateutil import rrule
from collections import defaultdict

class AltPoissonLogic(SimulationLogic):

    def __init__(self, session):
        SimulationLogic.__init__(self, session)

    def initialize(self, start_time, end_time):
        SimulationLogic.initialize(self, start_time, end_time)
        print "Loading Lambdas"
        self.lambda_distrs = self.load_lambdas(start_time, end_time)
        print "Loading Gammas"
        self.duration_distrs = self.load_gammas()
        print "Loading Destination Distrs"
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
        self.update_rebalance() 
        self.generate_new_trips(self.time)
        if self.rebalancing:
            self.rebalance_stations()

        self.resolve_trips()

        # Increment after we run for the current timestep?
        self.time += timestep

    def load_dest_distrs(self, start_time, end_time):
        '''
        Caches destination distributions into dictionary of day -> hour -> start_station_id -> [cumulative_distr, corresponding stations]
        # Change to a list of lists, faster, more space efficient
        '''
        distr_dict = [[{s_id:[] for s_id in self.stations.iterkeys()} for h in range(24)] for d in range(2)]


        # Inclusive
        #TODO figure out what to do if timespan > a week -> incline to say ignore it
        #TODO Bug: loading too much data at the moment, by a fair amount
        num_distrs = 0
        for day in rrule.rrule(rrule.DAILY, dtstart=start_time, until=end_time):
            dow = day.weekday()
            
            start_hour = start_time.hour if start_time.weekday() == dow else 0
            end_hour = end_time.hour if end_time.weekday() == dow else 24

            date_distrs = self.session.query(data_model.DestDistr) \
               .filter(DestDistr.year == day.year)\
               .filter(DestDistr.month == day.month)\
               .filter(DestDistr.is_week_day == (dow < 5)) \
               .filter(DestDistr.hour.between(start_hour, end_hour))\
               .yield_per(10000)

            for distr in date_distrs:
                result = distr_dict[distr.is_week_day][distr.hour][distr.start_station_id]

                # Unencountered  day, hour, start_station_id -> Create the list of lists containing distribution probability values and corresponding end station ids.
                if len(result) == 0:
                    distr_dict[distr.is_week_day][distr.hour][distr.start_station_id] = [[distr.prob], [distr.end_station_id]]
                else:
                    result[0].append(distr.prob)
                    result[1].append(distr.end_station_id)
                num_distrs += 1

            print "\t\tStarting reductions"
            # Change all of the probability vectors into cumulative probability vectors
            for hour in distr_dict[(dow < 5)]:
                for s_id, vectors in hour.iteritems():
                    # We have data for choosing destination vector
                    if len(vectors) == 2:
                        prob_vector = vectors[0]
                        # thanks to http://stackoverflow.com/questions/14132545/itertools-accumulate-versus-functools-reduce
                        # for basic accumulator code
                        cum_prob_vector = reduce(lambda a, x: a + [a[-1] + x], prob_vector[1:], [prob_vector[0]])
                        vectors[0] = cum_prob_vector
        print "Loaded %d distrs" % num_distrs
        return distr_dict


    def get_destination(self, s_id, time):
        '''
            Returns a destination station given dest_distrs
        '''
        #print time.day, time.hour, s_id
        vectors = self.dest_distrs[time.weekday() < 5][time.hour][s_id]
        if vectors:
            cum_prob_vector = vectors[0]
            station_vector = vectors[1]

            # cum_prob_vector[-1] should be 1 No scaling needed as described here:
            # http://docs.python.org/3/library/random.html (very bottom of page)
            # Scale it appropriately
            x = random.random() * cum_prob_vector[-1] 
        
            return station_vector[bisect.bisect(cum_prob_vector, x)]
        else:
            print "Error getting destination: Day",time.day,"hour",time.hour,"s_id",s_id
            # Send it to one of 273 randomly
            return random.choice(self.stations.keys())

    def generate_new_trips(self, start_time):
        for s_id in self.station_counts:
            lam = self.get_lambda(start_time.year, start_time.month,
                                  start_time.weekday(), start_time.hour, s_id)

            if lam:
                num_trips = self.get_num_trips(lam)
                for i in xrange(num_trips):
                    e_id = self.get_destination(s_id, start_time)
                    gamma = self.duration_distrs.get((s_id, e_id), None)
                    if gamma:
                        added_time = datetime.timedelta(seconds=random.randint(0, 3600))
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
        # HACK RIGHT NOW
        probability = random.random()
        while probability == 0:
            probability = random.random()

        # (4./3) * 
        num_trips = poisson.ppf(probability, 3600./lam.rate)

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

    def get_lambda(self, year, month, day, hour, start_station):
        '''
        If there is a lambda, return it. Otherwise return None as we only 
        load non-zero lambdas from the database for performance reasons.
        '''
        return self.lambda_distrs.get(year, {}).get(month, {}).get(day < 5, {}).get(hour, {}).get(start_station, None)

    def load_lambdas(self, start_time, end_time):
        '''
        Note: DB only has values > 0.
        '''
        # kind of gross but makes for easy housekeeping
        distr_dict = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(float)))))

        # keep track of when we've hit the database for a particular request
        requested_dict = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(bool))))

        num_added = 0

        for day in rrule.rrule(rrule.DAILY, dtstart=start_time, until=end_time):
            dow = day.weekday()
            
            start_hour = start_time.hour if start_time.weekday() == dow else 0
            end_hour = end_time.hour if end_time.weekday() == dow else 24

            year = day.year
            month = day.month
            is_week_day = dow < 5
            
            if not requested_dict[month][year][is_week_day][(start_hour, end_hour)]:
                lambda_poisson = self.session \
                                     .query(ExpLambda) \
                                     .filter(ExpLambda.month == month) \
                                     .filter(ExpLambda.year == year) \
                                     .filter(ExpLambda.is_week_day == is_week_day) \
                                     .filter(ExpLambda.hour.between(start_hour, end_hour))
                requested_dict[month][year][is_week_day][(start_hour, end_hour)] = True
                
            for lam in lambda_poisson:
                distr_dict[lam.year][lam.month][lam.is_week_day][lam.hour][lam.station_id] = lam
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
