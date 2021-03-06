#!/usr/bin/env python
'''
Jeff's Exponential Logic Idea
'''
import itertools
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

    def initialize(self, start_time, end_time, **kwargs):
        SimulationLogic.initialize(self, start_time, end_time, **kwargs)
        #TODO: Don't just hard-code the last day of data
        self.time_of_first_data = datetime.datetime(2010, 10, 01)
        self.time_of_last_data = datetime.datetime(2013, 07, 01)

        print "\tLoading Exp Distributions"
        self.exp_distrs = self.load_exp_lambdas(start_time, end_time)
        print "\tLoading gamma distributions"
        self.duration_distrs = self.load_gammas()
        print "\tLoading dest_distrs distributions"
        self.dest_distrs = self.load_dest_distrs(start_time, end_time)

        print "\tInitializing Trips"
        self.initialize_trips()
        self.moving_bikes = 0

    def update(self, timestep):
        '''Moves the simulation forward one timestep from given time'''
        self.rebalance_stations(self.time)
        # Increment after we run for the current timestep?
        self.time += timestep
        self.resolve_trips()

    def initialize_trips(self):
        hour = self.start_time.hour
        day = self.start_time.day
        for s_id in self.stations.iterkeys():
            new_trip = self.generate_trip(s_id, self.start_time)
            self.pending_departures.put((new_trip.start_date, new_trip))

    def generate_trip(self, s_id, time):
        # Check weekday or weekend
        idx = 0 if  time.weekday() < 5 else 1
        exp_l = self.exp_distrs[s_id][time.year][time.month]\
                               [time.weekday() < 5][time.hour] 

        # Never generated a trip, defer it until we have a feasible lambda
        # Test using if its greater than x hours too (possibly deal with bad latenight hours
        if not exp_l:# or exp_l.rate > 3600 * 2:
            # Test it out to see how this works
            # Have it look again the next hour
            return Trip('-1', "Casual", 2, time + datetime.timedelta(seconds=3601), 
                        None, s_id, s_id)

        # Returns time till next event in seconds
        # Function takes in 1/rate = "scale" but it works better the other way...
        wait_time = numpy.random.exponential(exp_l.rate*(3./4))
        #if wait_time > 3600:
        #    return Trip('-1', "Casual", 2, time + datetime.timedelta(seconds=3601), 
        #                None, s_id, s_id)

        trip_start_time = time + datetime.timedelta(seconds=wait_time)
        # It should go somewhere depending on when the hour of its start_time (could be far in the future)
        end_station_id = self._get_destination(s_id, trip_start_time)
        if end_station_id not in self.stations:
            print "ERROR END_ID",end_station_id,"NOT IN STATIONS, FROM s_id",s_id

        #print "Desire",(s_id,end_station_id)
        gamma = self.duration_distrs.get((s_id, end_station_id), None)
        if gamma:
            trip_duration = self.get_trip_duration(gamma)
            trip_end_time = trip_start_time + trip_duration

            #TODO Add new TripType 
            new_trip = data_model.Trip(str(random.randint(1,500)), 
                "Casual", 2, trip_start_time, trip_end_time, s_id, end_station_id)
        else:
            #print "GAMMA ERROR:"
            #print "Generate a trip from ",s_id,"for",wait_time,"seconds in the future"
            #print "start station",s_id,"end station",end_station_id
            #TODO !!! What to do if we've never seen trips between two stations????
            trip_end_time = trip_start_time
            new_trip = data_model.Trip(str(random.randint(1,500)), 
                "Casual", 2, trip_start_time, trip_end_time, s_id, end_station_id)
            #raise Exception("Gamma doesn't exist")
        return new_trip

    def _get_destination(self, s_id, time):
        '''
            Returns a destination station given dest_distrs
        '''
        vectors = self.dest_distrs[s_id][time.year][time.month][time.weekday() < 5][time.hour]
        if len(vectors) > 0:
            cum_prob_vector = vectors[0]
            station_vector = vectors[1]

            # http://docs.python.org/3/library/random.html (very bottom of page)
            x = random.random() * cum_prob_vector[-1]
        
            return station_vector[bisect.bisect(cum_prob_vector, x)]
        else:
            # Send it to one of 273 randomly
            return random.choice(self.stations.keys())


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
        Caches exp lambdas into dictionary of 
        s_id->year->month->[weekend, weekday]->hours
        '''
        # kind of gross but makes for easy housekeeping
        distr_dict = defaultdict(lambda: defaultdict(lambda: 
                        defaultdict(lambda: defaultdict(lambda: defaultdict(list)))))

        distrs = self.session.query(data_model.ExpLambda)\
                             .filter(ExpLambda.year >= start_time.year)\
                             .filter(ExpLambda.month >= start_time.month)\
                             .filter(ExpLambda.year <= end_time.year)\
                             .filter(ExpLambda.month <= end_time.month)\
                             .filter(ExpLambda.station_id.in_(self.stations.keys()))\
                             .yield_per(5000)

        num_ds = 0 
        for d in distrs:
            distr_dict[d.station_id][d.year][d.month][d.is_week_day][d.hour] = d
            num_ds += 1
        print "Loaded %i distributions" % num_ds
        return distr_dict

    def load_dest_distrs(self, start_time, end_time):
        '''
        Caches destination distributions into dictionary of day -> hour -> start_station_id -> [cumulative_distr, corresponding stations]
        # Change to a list of lists, faster, more space efficient
        '''
        time_diff = end_time - start_time 
        '''
        distr_dict = {y:{m:[[{s_id:[] for s_id in self.stations.iterkeys()} for h in range(24)]
                      for d in range(2)] for m in range(start_time.month, end_time.month + 1)}
                          for y in range(start_time.year, end_time.year + 1)}
        '''
        # Maps s_id->year->month->is_weekday->hour
        distr_dict = defaultdict(lambda: defaultdict(lambda: 
                        defaultdict(lambda: defaultdict(lambda: defaultdict(list)))))

        print "STARTING"
        # Inclusive
        #TODO figure out what to do if timespan > a week -> incline to say ignore it
        #TODO Bug: loading too much data at the moment, by a fair amount
        num_distrs = 0
        for day in rrule.rrule(rrule.DAILY, dtstart=start_time, until=end_time):
            dow = day.weekday()
            print "DAY?",day

            start_hour = start_time.hour if start_time.date == day.date else 0
            end_hour = end_time.hour if end_time.date == day.date else 24
            if start_hour == end_hour:
                print "BREAKING?"
                break

            if day > self.time_of_last_data:
                # TODO: work on this
                year = self.get_year_range_of_data(day.month)[-1]
            else:
                year = day.year
            print "Year", year

            date_distrs = self.session.query(data_model.DestDistr) \
               .filter(DestDistr.year == year)\
               .filter(DestDistr.month == day.month-1)\
               .filter(DestDistr.is_week_day == (dow < 5)) \
               .filter(DestDistr.hour.between(start_hour, end_hour))\
               .yield_per(10000)
            print "Start hour, end hour",start_hour,end_hour
            print date_distrs

            # TODO REMOVE count stuff
            count = 0
            s_count = 0
            for distr in date_distrs:
                count += 1
                # Faster to do this than be smart about the db query
                if distr.start_station_id in self.stations \
                        and distr.end_station_id in self.stations:
                    s_count += 1
                    result = distr_dict[distr.start_station_id][distr.year][distr.month+1][distr.is_week_day][distr.hour]

                    # Unencountered  day, hour, start_station_id -> Create the list of lists containing distribution probability values and corresponding end station ids.
                    if len(result) == 0:
                        distr_dict[distr.start_station_id][distr.year][distr.month+1][distr.is_week_day]\
                                  [distr.hour] = [[distr.prob], [distr.end_station_id]]
                    else:
                        result[0].append(distr.prob)
                        result[1].append(distr.end_station_id)
                    num_distrs += 1

            print "\t\tStarting reductions"
            # Change all of the probability vectors into cumulative probability vectors
            for s_id, s_id_info in distr_dict.iteritems():
                for hour, vectors in s_id_info[day.year][day.month][(dow < 5)].iteritems():
                    # We have data for choosing destination vector
                    if len(vectors) == 2:
                        prob_vector = vectors[0]
                        # thanks to http://stackoverflow.com/questions/14132545/itertools-accumulate-versus-functools-reduce
                        # for basic accumulator code
                        cum_prob_vector = reduce(lambda a, x: a + [a[-1] + x], prob_vector[1:], [prob_vector[0]])
                        vectors[0] = cum_prob_vector
        print "Loaded %d distrs" % num_distrs
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

        # No bike to depart on, log a dissapointment
        if self.station_counts[departure_station_ID] == 0:
            new_disappointment = Disappointment(departure_station_ID, trip.start_date, trip_id=None, is_full=False)
            self.session.add(new_disappointment)
            self.disappointments.append(new_disappointment)
            self.resolve_sad_departure(trip)

        # Using trip_end_time=None to indicate that we should just generate another trip
        # -> if it has an end_date then it's a normal trip
        elif trip.end_date:
            self.station_counts[departure_station_ID] -= 1
            self.pending_arrivals.put((trip.end_date, trip))
            # Perfect time to denote a now empty station
            if self.station_counts[departure_station_ID] == 0\
                   and not trip.start_station_id in self.unavailable_stations:
                self.unavailable_stations.add(departure_station_ID)
                self.empty_stations.put((trip.start_date, departure_station_ID))

        new_trip = self.generate_trip(departure_station_ID, trip.start_date)
        self.pending_departures.put((new_trip.start_date, new_trip))

    def clean_up(self):
        pass
