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
from scipy import stats
import numpy
import random
from simulation_logic import SimulationLogic
import datetime
from dateutil import rrule
from collections import defaultdict
import math
from sqlalchemy.sql import func,label

# Linear regression
LINEAR = 0
# Log regression using years as given
LOG1 = 1
# Log regression using year-2010+2
LOG2 = 2

class AltPoissonLogic(SimulationLogic):

    def __init__(self, session):
        SimulationLogic.__init__(self, session)

    def initialize(self, start_time, end_time, **kwargs):
        SimulationLogic.initialize(self, start_time, end_time, **kwargs)
        self.time_of_last_data = datetime.datetime(2013, 07, 01)
        print "Loading Lambdas"
        self.lambda_distrs = self.load_lambdas(start_time, end_time)
        print "Loading Gammas"
        self.duration_distrs = self.load_gammas()
        print "Loading Destination Distrs"
        self.dest_distrs = self.load_dest_distrs(start_time, end_time)
        self.moving_bikes = 0
        if end_time > self.time_of_last_data:
            self.regression_type = LOG2
            regression_data = self.init_regression_hardcoded()
            self.monthly_slope = regression_data[0]
            self.monthly_intercept = regression_data[1]


    def init_regression_hardcoded(self):
        # Hard-coded for LOG2, which worked best on one day of PoissonLogic...
        monthly_slope = [140162.706152, 94490.3697272, 160616.094567, 212792.877352, \
                             174981.220146, 177942.806166, 188861.264579, 206902.013367,\
                             239728.666726, 172147.381917, 108641.452414, 94129.8034996]
        monthly_intercept = [-123470.13792, -63016.7104916, -114170.211132, -161849.453422,\
                                  -89324.4690648, -89963.7202702, -103228.30612, -122760.094436,\
                                  -162961.869178, -90323.8821615, -40341.1279932, -43339.5275206]
        return monthly_slope, monthly_intercept


    def init_regression(self):
        # Returns slope and y-intercept for regression line for each month
        monthly_slope = []
        monthly_intercept = []
        for month in range(12):
            print "Calculated regression for month", month+1
            x_years = []
            y_counts = []
            month_data = self.session.query(func.count(Trip.id),
                         label('year', func.date_part('year', Trip.start_date)))\
                         .group_by(func.date_part('year', Trip.start_date))\
                         .filter(func.date_part('month', Trip.start_date)==month+1)\
                         .filter(Trip.trip_type_id == 1)
            for entry in month_data:
                # Entries look like (count, year)
                x_years.append(entry[1])
                y_counts.append(entry[0])

            slope, intercept = self.get_regression(x_years, y_counts)
            monthly_slope.append(slope)
            monthly_intercept.append(intercept)
        return monthly_slope, monthly_intercept


    def get_regression(self, x_list, y_list):
        if self.regression_type == LINEAR:
            return self.linear_regression(x_list, y_list)
        elif self.regression_type == LOG1:
            return self.log_regression(x_list, y_list)
        elif self.regression_type == LOG2:
            return self.log_regression_with_year_deltas(x_list, y_list)


    def linear_regression(self, x_list, y_list):
        slope, intercept, r_val, p_val, std_err = stats.linregress(x_list, y_list)
#        print "Slope", slope                       
#        print "Intercept", intercept
#        print "R val", r_val, "\t P val", p_val, "\t Std err", std_err
        return slope, intercept


    def log_regression(self, x_list, y_list):
        # Using years as given
        log_x_list = []
        for x in x_list:
            log_x_list.append(math.log(x))
        return self.linear_regression(log_x_list, y_list)


    def log_regression_with_year_deltas(self, x_list, y_list):
        # Using log of 2, 3, 4, 5 as x instead of log of 2010, 2011, 2012, 2013, since log graphs are constrained by (0,undefined) and (1,0)
        log_x_list = []
        for x in x_list:
            log_x_list.append(math.log(x-2010+2))
        return self.linear_regression(log_x_list, y_list)

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
        time_diff = end_time - start_time 
        distr_dict = {y:{m:[[{s_id:[] for s_id in self.stations.iterkeys()} for h in range(24)]
                      for d in range(2)] for m in range(start_time.month, end_time.month + 1)}
                          for y in range(start_time.year, end_time.year + 1)}

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
                # Faster to do this than be smart about the db query
                if distr.start_station_id in self.stations \
                        and distr.end_station_id in self.stations:
                    result = distr_dict[distr.year][distr.month][distr.is_week_day][distr.hour][distr.start_station_id]

                    # Unencountered  day, hour, start_station_id -> Create the list of lists containing distribution probability values and corresponding end station ids.
                    if len(result) == 0:
                        distr_dict[distr.year][distr.month][distr.is_week_day]\
                                  [distr.hour][distr.start_station_id] = [[distr.prob], [distr.end_station_id]]
                    else:
                        result[0].append(distr.prob)
                        result[1].append(distr.end_station_id)
                    num_distrs += 1

            print "\t\tStarting reductions"
            # Change all of the probability vectors into cumulative probability vectors
            for hour in distr_dict[day.year][day.month][(dow < 5)]:
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


    def _get_destination(self, s_id, time):
        '''
            Returns a destination station given dest_distrs
        '''
        #print time.day, time.hour, s_id
        vectors = self.dest_distrs[time.year][time.month][time.weekday() < 5][time.hour][s_id]
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
            if start_time > self.time_of_last_data:
                lam = self.predict_future_lambda(start_time, s_id)
            else:
                lam = self.get_lambda(start_time.year, start_time.month,
                                  start_time.weekday(), start_time.hour, s_id)
            if lam:
                num_trips = self.get_num_trips(lam)
                for i in xrange(num_trips):
                    e_id = self._get_destination(s_id, start_time)
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
    

    def predict_future_lambda(self, start_time, station_id):
        month = start_time.month
        slope = self.monthly_slope[month-1]
        intercept = self.monthly_intercept[month-1]
        lam_prediction = 0
        for prev_year in self.get_year_range_of_data(month):
            prev_year_lambda = self.get_lambda(prev_year, month, start_time.weekday(), start_time.hour, station_id)
            if not prev_year_lambda: continue
            lam_prediction += self.predict_from_one_year(prev_year, prev_year_lambda, slope, intercept, start_time)

        lam_prediction /= len(self.get_year_range_of_data(month))
        if lam_prediction <= 0:
            return None
        return ExpLambda(station_id, start_time.year, start_time.month, start_time.weekday()<5, start_time.hour, lam_prediction)


    def predict_from_one_year(self, prev_year, prev_year_lambda, slope, intercept, start_time):
        if self.regression_type == LINEAR:
            return self.linear_predict(prev_year, prev_year_lambda, slope, intercept, start_time)
        elif self.regression_type == LOG1:
            return self.log_predict(prev_year, prev_year_lambda, slope, intercept, start_time)
        elif self.regression_type == LOG2:
            return self.log_predict_with_year_deltas(prev_year, prev_year_lambda, slope, intercept, start_time)


    def linear_predict(self, prev_year, prev_year_lambda, slope, intercept, start_time):
        prev_year_trips = slope * prev_year + intercept
        future_year_trips = slope * start_time.year + intercept
        lam_prediction = prev_year_lambda.rate * future_year_trips / prev_year_trips
        return lam_prediction


    def log_predict(self, prev_year, prev_year_lambda, slope, intercept, start_time):
        prev_year_trips = slope * math.log(prev_year) + intercept
        future_year_trips = slope * math.log(start_time.year) + intercept
        lam_prediction = prev_year_lambda.rate * future_year_trips / prev_year_trips
        return lam_prediction


    def log_predict_with_year_deltas(self, prev_year, prev_year_lambda, slope, intercept, start_time):
        # Hopefully these are reasonable 
        prev_year_trips = slope * math.log(prev_year-2010+2) + intercept
        future_year_trips = slope * math.log(start_time.year-2010+2) + intercept
        lam_prediction = prev_year_lambda.rate * future_year_trips / prev_year_trips
        return lam_prediction


    def get_year_range_of_data(self, month):
        #TODO: Don't just hard-code dates of existing data                                                   
        if month >= 10:
            return [2010, 2011, 2012]
        elif month <= 6:
            return [2011, 2012, 2013]
        else:
            return [2011, 2012]


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
        station_list = self.stations.keys()
        
        # If future, load lambdas for that time every year
        if end_time > self.time_of_last_data:
            if start_time > self.time_of_last_data: dt_start = start_time
            else: dt_start = self.time_of_last_data
            print "The future is now"
            for day in rrule.rrule(rrule.DAILY, dtstart=dt_start, until=end_time):
                dow = day.weekday()
                
                start_hour = dt_start.hour if dt_start.weekday() == dow else 0
                end_hour = end_time.hour if end_time.weekday() == dow else 24

                month = day.month
                year = day.year
                is_week_day = dow < 5
                if not requested_dict[month][year][is_week_day][(start_hour, end_hour)]:
                    lambda_poisson = self.session.query(ExpLambda)\
                        .filter(ExpLambda.is_week_day == is_week_day)\
                        .filter(ExpLambda.month == month)\
                        .filter(ExpLambda.hour.between(start_hour, end_hour))\
                        .filter(ExpLambda.station_id.in_(station_list))
                    requested_dict[month][year][is_week_day][(start_hour, end_hour)] = True

                for lam in lambda_poisson:
                    distr_dict[lam.year][lam.month][lam.is_week_day][lam.hour][lam.station_id] = lam
                    num_added += 1
                            
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
                                     .filter(ExpLambda.hour.between(start_hour, end_hour))\
                                     .filter(ExpLambda.station_id.in_(station_list))
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
