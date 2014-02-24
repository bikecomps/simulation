#!/usr/bin/env python
'''
    poisson_logic.py

    Questions we still have about distributions:
    - Do we have to specify standard deviation and whatever the poisson equivalent is? (Perhaps we use scipy's rvs function but I haven't figured it out yet.)
'''
from utils import Connector
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
from dateutil.relativedelta import relativedelta

# Linear regression
LINEAR = 0
# Log regression using years as given
LOG1 = 1
# Log regression using year-2010+2
LOG2 = 2
# Simply pretend it's 2013 (or 2012 if month > 6)
LASTYEAR = 3
# Log regression, but only extrapolating from 2013 (or 2012 if month > 6)
LOGLASTYEAR = 4
# Linear regression, but only extrapolating from the last year of data for that month
LINEARLASTYEAR = 5
# Log regression, but predicting based on actual prev_month values instead of ones from regression line
LOGREALYEARS = 6
# Jeff's suggestion to do regression over year-long chunks starting at each month
JEFF = 7
# Do regression for each individual lambda. This is fairly bad.
OLD = 8


class PoissonLogic(SimulationLogic):


    def __init__(self, session):
        SimulationLogic.__init__(self, session)


    def initialize(self, start_time, end_time, **kwargs):
        SimulationLogic.initialize(self, start_time, end_time, **kwargs)
        #TODO: Don't just hard-code the last day of data
        self.time_of_first_data = datetime.datetime(2010, 10, 01)
        self.time_of_last_data = datetime.datetime(2013, 07, 01)
        print "Starting to load lambdas"
        self.lambda_distrs = self.load_lambdas(start_time, end_time)
        print "Loaded Lambdas"
        self.duration_distrs = self.load_gammas()
        print "Loaded Gammas"
        self.moving_bikes = 0
        if end_time > self.time_of_last_data:
            self.regression_type = LINEAR
            regression_data = self.init_regression()
            self.monthly_slope = regression_data[0]
            self.monthly_intercept = regression_data[1]


    def init_regression(self):
        if self.regression_type == LINEAR or self.regression_type == LINEARLASTYEAR:
            return self.init_regression_LINEAR_hardcoded()
        elif self.regression_type == LOG2 or self.regression_type == LOGLASTYEAR or self.regression_type == LOGREALYEARS:
            return self.init_regression_LOG2_hardcoded()
        elif self.regression_type == JEFF:
            return self.init_regression_jeff()
        elif self.regression_type == OLD:
            return [None, None]
        else:
            return self.init_regression_with_calculations()


    def init_regression_jeff(self):
        # for month of data:
        #     get riders within a year after that month including it
        #     x = the month number
        #     y = riders
        #     get the percentage of rides that happen in that month (for all years)
        # do regression, it will just return one slope and one intercept

        # num_months = (self.time_of_last_data.year - self.time_of_first_data.year - 1) * 12 + \
        #             self.time_of_last_data.month - self.time_of_first_data.month
        # x_months = []
        # y_trips = []
        # for month in range(num_months):
        #     year_start = self.time_of_first_data + relativedelta(months=month)
        #     year_end = year_start + relativedelta(months=12) - datetime.timedelta(days=1)
        #     print "Start:", year_start, "\tEnd:", year_end
        #     data = self.session.query(func.count(Trip.id))\
        #                         .filter(Trip.start_date > year_start)\
        #                         .filter(Trip.start_date < year_end)
        #     x_months.append(month)
        #     y_trips.append(data[0][0])
        #     print "month", month, "trips", data[0][0]
        # print "x_year_chunks:", x_months, "y_trips:", y_trips
        # slope, intercept = self.linear_regression(x_months, y_trips)
        # print "Slope:", slope, "\tIntercept:", intercept

        # # TODO: you are currently getting the fraction of trips that happen each month incorrectly because some of the months appear 3 times and some appear 2 times, so the 3x months will be falsely higher percentage...but do you even need this?
        # self.percent_trips_per_month = [0] * 12
        # total_trips = 0
        # for month in range(12):
        #     # Find the percentage of trips that happen in that month
        #     month_data = self.session.query(func.count(Trip.id))\
        #                         .filter(func.date_part('month', Trip.start_date) == month+1)\
        #                         .filter(Trip.trip_type_id == 1)
        #     self.percent_trips_per_month[month] = month_data[0][0]
        #     total_trips += month_data[0][0]
        # for month in range(12):
        #     self.percent_trips_per_month[month] /= float(total_trips)
        # print "Trips per month:", self.percent_trips_per_month
        slope = 59980.791
        intercept = 1085035.710
        return [slope], [intercept]


    def init_regression_LINEAR_hardcoded(self):
        monthly_slope = [35509.5, 23624.5, 39366.5, 54723.500000000007, 44956.5, 45747.0, 54332.0, 59522.0, 83251.0, 60082.5, 38135.500000000007, 32221.000000000004]
        monthly_intercept = [-71377292.666666672, -47466552.0, -79100362.333333328, -109975115.66666669, -90302991.333333328, -91890074.666666672, -109157395.0, -119594197.0, -167326766.0, -120733866.83333333, -76615742.166666687, -64740054.000000007]
        self.monthly_trips = {2010: [0, 0, 0, 0, 0, 0, 0, 0, 4023L, 31055L, 37324L, 19943L], 2011: [28510L, 37268L, 50827L, 74510L, 104738L, 107588L, 104257L, 104545L, 98437L, 93847L, 73326L, 64803L], 2012: [75425L, 76041L, 134720L, 127232L, 149071L, 151998L, 158589L, 164067L, 170525L, 151220L, 113595L, 84385L], 2013: [99529L, 84517L, 129560L, 183957L, 194651L, 199082L]}
        return monthly_slope, monthly_intercept


    def init_regression_LOG2_hardcoded(self):
        # Hard-coded for LOG2 regression, which I chose based on very little data because it seemed to work best for one day.
        monthly_slope = [140162.706152, 94490.3697272, 160616.094567, 212792.877352, \
                             174981.220146, 177942.806166, 188861.264579, 206902.013367,\
                             239728.666726, 172147.381917, 108641.452414, 94129.8034996]
        monthly_intercept = [-123470.13792, -63016.7104916, -114170.211132, -161849.453422,\
                                  -89324.4690648, -89963.7202702, -103228.30612, -122760.094436,\
                                  -162961.869178, -90323.8821615, -40341.1279932, -43339.5275206]
        self.monthly_trips = {2010: [0, 0, 0, 0, 0, 0, 0, 0, 4023L, 31055L, 37324L, 19943L], 2011: [28510L, 37268L, 50827L, 74510L, 104738L, 107588L, 104257L, 104545L, 98437L, 93847L, 73326L, 64803L], 2012: [75425L, 76041L, 134720L, 127232L, 149071L, 151998L, 158589L, 164067L, 170525L, 151220L, 113595L, 84385L], 2013: [99529L, 84517L, 129560L, 183957L, 194651L, 199082L]}
        return monthly_slope, monthly_intercept


    def init_regression_with_calculations(self):
        # Returns slope and y-intercept for regression line for each month
        monthly_slope = []
        monthly_intercept = []
        self.monthly_trips = {2010:[], 2011:[], 2012:[], 2013:[]}
        for month in range(12):
            print "Calculating regression for month", month+1
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
                self.monthly_trips[entry[1]].append(entry[0])
            print "X_years", x_years, "\tY_counts", y_counts

            slope, intercept = self.get_regression(x_years, y_counts)
            monthly_slope.append(slope)
            monthly_intercept.append(intercept)
        print "Monthly trips:", self.monthly_trips
        return monthly_slope, monthly_intercept


    def get_regression(self, x_list, y_list):
        if self.regression_type == LINEAR:
            return self.linear_regression(x_list, y_list)
        elif self.regression_type == LOG1:
            return self.log_regression(x_list, y_list)
        elif self.regression_type == LOG2:
            return self.log_regression_with_year_deltas(x_list, y_list)
        else:
            print "Not a valid regression type"

    def linear_regression(self, x_list, y_list):
        slope, intercept, r_val, p_val, std_err = stats.linregress(x_list, y_list)
        print "Slope", slope
        print "Intercept", intercept
        print "R val", r_val, "\t P val", p_val, "\t Std err", std_err
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
        #print "Num bikes at stations", sum([x for x in self.station_counts.itervalues()])
        #print "Num bikes in transit", self.pending_arrivals.qsize()
        #print "Moving bikes", self.moving_bikes
        #print "Total?", sum([x for x in self.station_counts.itervalues()]) + self.pending_arrivals.qsize() + self.moving_bikes
        #print "Stations with more count than cap? ", len([s_id for s_id, count in self.station_counts.iteritems() if count > self._get_station_cap(s_id)])
        #print [(count, self._get_station_cap(s_id)) for s_id, count in self.station_counts.iteritems()]

        """
        x = len(self.unavailable_stations)
        if x > 0:
            print "BEFORE: Num unavailable", x
            """
        self.rebalance_stations(self.time)
        """
        if x > 0:
            print "AFTER: Num unavailable", len(self.unavailable_stations)
            """
        self.generate_new_trips(self.time)
        self.time+=timestep
        self.resolve_trips()


    def generate_new_trips(self, start_time):
        # Note that Monday is day 0 and Sunday is day 6. Is this the same for data_model?
#        self.print_lambda_dict()
        station_count = 0
        for start_station_id in self.station_counts:
            station_count += 1
            for end_station_id in self.station_counts:
                # Check if predicting a future date 
                if start_time > self.time_of_last_data:
                    lam = self.predict_future_lambda(start_time, start_station_id, end_station_id)
                else:    
                    lam = self.get_lambda(start_time.year, start_time.month,
                                          start_time.weekday(), start_time.hour,
                                          start_station_id, end_station_id)
                gamma = self.duration_distrs.get((start_station_id, end_station_id), None)
                # Check for invalid queries
                if lam and gamma:
                    num_trips = self.get_num_trips(lam)
 #                   print "lambda =", lam, " & ", num_trips, "trips during", start_time
                    for i in range(num_trips):
                        # Starting time of the trip is randomly chosen within the Lambda's time range, which is hard-coded to be an hour.
                        added_time = datetime.timedelta(minutes=random.randint(0, 59), seconds=random.randint(0, 59))
                        trip_start_time = start_time + added_time
                        trip_duration = self.get_trip_duration(gamma)
                        trip_end_time = trip_start_time + trip_duration
                        new_trip = Trip(str(random.randint(1,500)), "Casual", 2, \
                                trip_start_time, trip_end_time, start_station_id, end_station_id)
                        self.pending_departures.put((trip_start_time, new_trip))


    def predict_future_lambda(self, start_time, start_station_id, end_station_id):
        month = start_time.month
        if self.regression_type == JEFF:
            slope = self.monthly_slope[0]
            intercept = self.monthly_intercept[0]
        else:
            slope = self.monthly_slope[month-1]
            intercept = self.monthly_intercept[month-1]
        lam_prediction = 0
        if self.regression_type == LASTYEAR or self.regression_type == LOGLASTYEAR or self.regression_type == LINEARLASTYEAR:
            lam_prediction = self.predict_from_last_year(start_time, start_station_id, end_station_id)
        elif self.regression_type == OLD:
            lam_prediction = self.old_predict(start_time, start_station_id, end_station_id)
        else:
            for prev_year in self.get_year_range_of_data(month):
                prev_year_lambda = self.get_lambda(prev_year, month, start_time.weekday(), start_time.hour, start_station_id, end_station_id) 
                if not prev_year_lambda: continue
                lam_prediction += self.predict_from_one_year(prev_year, prev_year_lambda, slope, intercept, start_time)
            lam_prediction /= len(self.get_year_range_of_data(month))

        if lam_prediction <= 0:
            return None
        return Lambda(start_station_id, end_station_id, start_time.hour, start_time.weekday()<5, start_time.year, month, lam_prediction)


    def predict_from_last_year(self, start_time, start_station_id, end_station_id):
        year = 2013 if start_time.month <= 6 else 2012
        lam = self.get_lambda(year, start_time.month, start_time.weekday(), start_time.hour, start_station_id, end_station_id)
        if not lam: return 0
        slope = self.monthly_slope[start_time.month-1]    
        intercept = self.monthly_intercept[start_time.month-1]
        if self.regression_type == LASTYEAR:
            return lam.value
        elif self.regression_type == LOGLASTYEAR:
            return self.log_predict_with_year_deltas(2013, lam, slope, intercept, start_time)
        elif self.regression_type == LINEARLASTYEAR:
            return self.linear_predict(2013, lam, slope, intercept, start_time)


    def predict_from_one_year(self, prev_year, prev_year_lambda, slope, intercept, start_time):
        if self.regression_type == LINEAR:
            return self.linear_predict(prev_year, prev_year_lambda, slope, intercept, start_time)
        elif self.regression_type == LOG1:
            return self.log_predict(prev_year, prev_year_lambda, slope, intercept, start_time)
        elif self.regression_type == LOG2:
            return self.log_predict_with_year_deltas(prev_year, prev_year_lambda, slope, intercept, start_time)
        elif self.regression_type == LOGREALYEARS:
            return self.log_predict_with_real_years(prev_year, prev_year_lambda, slope, intercept, start_time)
        elif self.regression_type == JEFF:
            return self.jeff_predict(prev_year, prev_year_lambda, slope, intercept, start_time)


    def jeff_predict(self, prev_year, prev_year_lambda, slope, intercept, start_time):
        # Get the predicted total number of trips per year
        # Get the fraction of trips that happen that month
        # TODO: Check your logic if you're getting the correct month for prev and future_year_trips
        # Predicting month n means the year chunk should start at month n-6
        future_month = (start_time.year - self.time_of_first_data.year) * 12 + \
                    start_time.month - self.time_of_first_data.month - 5
        prev_month = future_month - 12
        prev_year_trips = slope * prev_month + intercept
        future_year_trips = slope * future_month + intercept
        lam_prediction = prev_year_lambda.value * future_year_trips / prev_year_trips
        return lam_prediction


    def linear_predict(self, prev_year, prev_year_lambda, slope, intercept, start_time):
        prev_year_trips = slope * prev_year + intercept
        future_year_trips = slope * start_time.year + intercept
        lam_prediction = prev_year_lambda.value * future_year_trips / prev_year_trips
        return lam_prediction


    def log_predict(self, prev_year, prev_year_lambda, slope, intercept, start_time):
        prev_year_trips = slope * math.log(prev_year) + intercept
        future_year_trips = slope * math.log(start_time.year) + intercept
        lam_prediction = prev_year_lambda.value * future_year_trips / prev_year_trips
        return lam_prediction

    
    def log_predict_with_year_deltas(self, prev_year, prev_year_lambda, slope, intercept, start_time):
        # Hopefully these are reasonable
        prev_year_trips = slope * math.log(prev_year-2010+2) + intercept
        future_year_trips = slope * math.log(start_time.year-2010+2) + intercept
        lam_prediction = prev_year_lambda.value * future_year_trips / prev_year_trips
        return lam_prediction


    def log_predict_with_real_years(self, prev_year, prev_year_lambda, slope, intercept, start_time):
        prev_year_trips = self.monthly_trips[prev_year][start_time.month-1]
        future_year_trips = slope * math.log(start_time.year-2010+2) + intercept
        lam_prediction = prev_year_lambda.value * future_year_trips / prev_year_trips
        return lam_prediction


    def old_predict(self, start_time, start_station_id, end_station_id):
        x_dates = []
        y_lambdas = []
        #TODO: Don't hard-code year that the data starts and ends
#        print "Start time:", start_time, "Stations:", start_station_id, end_station_id
        for year in range(2010, 2014):
            lam = self.get_lambda(year, start_time.month, start_time.weekday(), start_time.hour, start_station_id, end_station_id)
#            print year, start_time.hour, lam
            x_dates.append(year)
            y_lambdas.append(lam.value if lam else 0)
           
        if len(x_dates) == 0:
            return 0
        # If not using log regression, remove the math.log calls 
        for i in range(len(x_dates)):
           x_dates[i] = math.log(x_dates[i])
        slope, intercept, r_val, p_val, std_err = stats.linregress(x_dates, y_lambdas)
        new_lam_val = slope * math.log(start_time.year) + intercept

#        for i in range(len(x_dates)):
#            print x_dates[i], y_lambdas[i]
        # slope, intercept, r_val, p_val, std_err = stats.linregress(x_dates, y_lambdas)
        # new_lam_val = slope * start_time.year + intercept
#        print slope, intercept, new_lam_val
        if new_lam_val <= 0:
            new_lam_val = self.avg_lambda(y_lambdas)
        return Lambda(start_station_id, end_station_id, start_time.hour, start_time.weekday()<5, start_time.year, start_time.month, new_lam_val)


    def get_year_range_of_data(self, month):
        #TODO: Don't just hard-code dates of existing data
        if month >= 10:
            return [2010, 2011, 2012]
        elif month <= 6:
            return [2011, 2012, 2013]
        else:
            return [2011, 2012]


    def get_month_range_of_data(self, year):
        if year == 2010:
            return range(10,13)
        elif year == 2013:
            return range(1,7)
        elif year == 2011 or year == 2012:
            return range(1,13)
        else:
            return []


    def get_num_trips(self, lam):
        """
        Samples a poisson distribution with the given lambda and returns the number
        of trips produced from the dist. Returns -1 if lambda = 0 -> undefined function.
        """
        probability = random.random()
        while probability == 0:
            probability = random.random()
            
        # when using all data (training + testing)
        # num_trips = poisson.ppf(probability, lam.value)

        # when using only training data
        num_trips = poisson.ppf(probability, lam.value * (4./3))

        if numpy.isnan(num_trips):
            num_trips = -1
        return int(round(num_trips))


    def load_gaussians(self):
        """
        Caches gaussian distribution values into a dictionary.
        """
        gaussian_distr = self.session.query(GaussianDistr)\
                             .filter(GaussianDistr.start_station_id.in_(self.stations.keys()))

        distr_dict = {}
        for gauss in gaussian_distr:
            distr_dict[(gauss.start_station_id, gauss.end_station_id)] = gauss
        return distr_dict

    def load_gammas(self):
        '''
        Caches gaussian distribution variables into a dictionary.
        '''
        gamma_distr = self.session.query(Gamma)\
                          .filter(Gamma.start_station_id.in_(self.stations.keys()))

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
        print "Start time",start_time, "End time",end_time
        # kind of gross but makes for easy housekeeping
        distr_dict = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(float)))))

        # keep track of when we've hit the database for a particular request
        requested_dict = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(bool))))

        num_added = 0
        # Inclusive
        
        print start_time, end_time
        
        # If some part of the simulation is in the future, load lambdas for that time
        # every year so regression can be done later
        if end_time > self.time_of_last_data:
            if start_time > self.time_of_last_data: dt_start = start_time
            else: dt_start = self.time_of_last_data            
            print "The future is now"
            for day in rrule.rrule(rrule.DAILY, dtstart=dt_start, until=end_time):
                dow = day.weekday()
                
                start_hour = dt_start.hour if dt_start.weekday() == dow else 0
                end_hour = end_time.hour if end_time.weekday() == dow else 24
    
                month = day.month
                is_week_day = dow < 5
                
                lambda_poisson = self.session.query(data_model.Lambda) \
                    .filter(data_model.Lambda.is_week_day == is_week_day) \
                    .filter(data_model.Lambda.month == month) \
                    .filter(data_model.Lambda.hour.between(start_hour, end_hour))
  
                for lam in lambda_poisson:
                    distr_dict[lam.year][month][lam.is_week_day][lam.hour][(lam.start_station_id, lam.end_station_id)] = lam
                    num_added += 1
                        

        station_list = self.stations.keys()
        for day in rrule.rrule(rrule.DAILY, dtstart=start_time, until=end_time):
            dow = day.weekday()
            
            start_hour = start_time.hour if start_time.weekday() == dow else 0
            end_hour = end_time.hour if end_time.weekday() == dow else 24

            year = day.year
            month = day.month
            is_week_day = dow < 5

            # For now we're only loading in lambdas that have non-zero values. 
            # We'll assume zero value if it's not in the dictionary
            lambda_poisson = self.session.query(data_model.Lambda) \
                .filter(data_model.Lambda.is_week_day == is_week_day) \
                .filter(data_model.Lambda.year == year) \
                .filter(data_model.Lambda.month == month) \
                .filter(data_model.Lambda.hour.between(start_hour, end_hour))        
            
            if not requested_dict[month][year][is_week_day][(start_hour, end_hour)]:
                lambda_poisson = self.session \
                                     .query(Lambda) \
                                     .filter(Lambda.month == month) \
                                     .filter(Lambda.year == year) \
                                     .filter(Lambda.is_week_day == is_week_day) \
                                     .filter(Lambda.hour.between(start_hour, end_hour))\
                                     .filter(Lambda.start_station_id.in_(station_list))\
                                     .filter(Lambda.end_station_id.in_(station_list))
                requested_dict[month][year][is_week_day][(start_hour, end_hour)] = True
                
            for lam in lambda_poisson:
                distr_dict[lam.year][lam.month][lam.is_week_day][lam.hour][(lam.start_station_id, lam.end_station_id)] = lam
                num_added += 1

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


if __name__ == '__main__':
    main()
