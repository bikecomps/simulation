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

    def initialize(self, start_time, end_time):
        SimulationLogic.initialize(self, start_time, end_time)
        print "\tLoading Exp Distributions"
        self.exp_distrs = self.load_exp_lambdas(start_time, end_time)
        print "\tLoading gamma distributions"
        self.duration_distrs = self.load_gammas()
        print "\tLoading dest_distrs distributions"
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

        print "\tInitializing Trips"
        #TODO Generate initial trips for every station
        self.initialize_trips()


    def update(self, timestep):
        '''Moves the simulation forward one timestep from given time'''
        self.resolve_trips()

        # Increment after we run for the current timestep?
        self.time += timestep

    def initialize_trips(self):
        '''
        for s_id,els in self.exp_distrs.iteritems():
            print s_id
            for el in els:
                print "\t",el
        '''
        hour = self.start_time.hour
        day = self.start_time.day
        print "INIT",day,hour,self.start_time
        for s_id in self.stations.iterkeys():
            new_trip = self.generate_trip(s_id, self.start_time)
            self.pending_departures.put((new_trip.start_date, new_trip))
        print "NO MORE INIT TRIPS"

    def _generate_trip(self, s_id, time):
        # Check weekday or weekend
        idx = 0 if  time.weekday() < 5 else 1
        exp_l = self.exp_distrs[s_id][time.year][time.month]\
                               [time.weekday() < 5][time.hour] 

        # Never generated a trip, defer it until we have a feasible lambda
        # Test using if its greater than x hours too (possibly deal with bad latenight hours
        if not exp_l or exp_l.rate > 3600 * 3:
            # Test it out to see how this works
            # Have it look again the next hour
            return Trip('-1', "Casual", 2, time + datetime.timedelta(seconds=3600), 
                        None, s_id, s_id)

        # Returns time till next event in seconds
        # Function takes in 1/rate = "scale" but it works better the other way...
        wait_time = numpy.random.exponential(exp_l.rate*(3./4))
        '''
        if wait_time > 3600:
            return Trip('-1', "Casual", 2, time + datetime.timedelta(seconds=3600), 
                        None, s_id, s_id)
        '''

        trip_start_time = time + datetime.timedelta(seconds=wait_time)
        # It should go somewhere depending on when the hour of its start_time (could be far in the future)
        end_station_id = self.get_destination(s_id, trip_start_time)

        #print "Desire",(s_id,end_station_id)
        gamma = self.duration_distrs.get((s_id, end_station_id), None)
        if gamma:
            trip_duration = self.get_trip_duration(gamma)
            trip_end_time = trip_start_time + trip_duration

            #TODO Add new TripType 
            new_trip = data_model.Trip(str(random.randint(1,500)), 
                "Casual", 2, trip_start_time, trip_end_time, s_id, end_station_id)
        else:
            print "GAMMA ERROR:"
            print "start station",s_id,"end station",end_station_id
            #TODO !!! What to do if we've never seen trips between two stations????
            trip_end_time = trip_start_time
            new_trip = data_model.Trip(str(random.randint(1,500)), 
                "Casual", 2, trip_start_time, trip_end_time, s_id, end_station_id)
            #raise Exception("Gamma doesn't exist")
        return new_trip

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
        distr_dict = {s:[[None]*24, [None]*24] for s in self.stations.iterkeys()}
        distr_dict = {s: {y:[[[None] * 24, [None] * 24] for m in range(12)] 
                           for y in xrange(start_time.year, end_time.year + 1)} 
                           for s in self.stations.iterkeys()}

        distrs = self.session.query(data_model.ExpLambda)\
                             .filter(ExpLambda.year >= start_time.year)\
                             .filter(ExpLambda.month >= start_time.month)\
                             .filter(ExpLambda.year <= end_time.year)\
                             .filter(ExpLambda.month <= end_time.month)\
                             .yield_per(5000)

        
        for d in distrs:
            distr_dict[d.station_id][d.year][d.month][d.is_weekday][d.hour] = d

        return distr_dict

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


        # Using trip_end_time=None to indicate that we should just generate another trip
        if not trip.end_date:
            new_trip = self.generate_trip(departure_station_ID, trip.start_date)
            self.pending_departures.put((new_trip.start_date, new_trip))
        elif self.station_counts[departure_station_ID] == 0:
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
    main()
