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

LINEAR = 0
LOG1 = 1
LOG2 = 2


class PoissonLogic(SimulationLogic):
    #TODO: Don't just hard-code the last day of data

    def __init__(self, session):
        SimulationLogic.__init__(self, session)

    def initialize(self, start_time, end_time):
        SimulationLogic.initialize(self, start_time, end_time)
        self.time_of_last_data = datetime.datetime(2013, 07, 01)
        self.lambda_distrs = self.load_lambdas(start_time, end_time)
        self.duration_distrs = self.load_gammas()
        # Retrieve StationDistance objects representing the five closest
        # stations for each stations.
        self.nearest_station_dists = {}
        station_list = self.session.query(data_model.Station) 
        for station in station_list:
            nearest_distances = self.session.query(data_model.StationDistance)\
                    .filter(data_model.StationDistance.station1_id == station.id)\
                    .order_by(data_model.StationDistance.distance)[:8]
            self.nearest_station_dists[station.id] = nearest_distances
        if end_time > self.time_of_last_data:
            regression_data = self.init_regression()
            self.monthly_slope = regression_data[0]
            self.monthly_intercept = regression_data[1]
        self.moving_bikes = 0
        

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

            slope, intercept = self.log_regression_with_year_deltas(x_years, y_counts)
            monthly_slope.append(slope)
            monthly_intercept.append(intercept)
        return monthly_slope, monthly_intercept


    def linear_regression(self, x_list, y_list):
        slope, intercept, r_val, p_val, std_err = stats.linregress(x_list, y_list)
#        print "X", x_list
#        print "Y", y_list
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
        not_full = []
        not_empty = []
        for s_id in self.station_counts:
            if self.station_counts[s_id] > 0 and s_id in self.empty_stations_set:
                not_empty.append(s_id)
                self.empty_stations_set.remove(s_id)      
            elif self.station_counts[s_id] != self.stations[s_id].capacity and s_id in self.full_stations_set:
                not_full.append(s_id)
                self.full_stations_set.remove(s_id)
            elif self.station_counts[s_id] == self.stations[s_id].capacity and s_id not in self.full_stations_set:
                self.full_stations_set.add(s_id)
            elif self.station_counts[s_id] == 0 and s_id not in self.empty_stations_set:
                self.empty_stations_set.add(s_id)
        if len(not_full) > 0:
            print "\tNo longer full:\n" + "\t\t" + str(list(not_full))
        if len(not_empty) > 0:
                print "\tNo longer empty:\n" + "\t\t" + str(list(not_empty))
        if len(self.full_stations_set) > 0:
                print "\tNow full:\n" + "\t\t" + str(list(self.full_stations_set))
        if len(self.empty_stations_set) > 0:
            print "\tNow empty:\n" + "\t\t" + str(list(self.empty_stations_set))
        if self.rebalancing:
            self.rebalance_stations()
        # print "\tPost rebalance. Moving bikes:", self.moving_bikes
        #if len(self.full_stations_set) > 0:
        #        print "\t\tNow full:\n" + "\t\t" + str(self.full_stations_set)
        #if len(self.empty_stations_set) > 0:
        #    print "\t\tNow empty:\n" + "\t\t" + str(self.empty_stations_set)
        self.generate_new_trips(self.time)
        if self.rebalancing:
            self.rebalance_stations()
        self.resolve_trips()

        # Increment after we run for the current timestep?
        self.time += timestep


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
                        added_time = datetime.timedelta(0, random.randint(0, 59),
                                                        0, 0, random.randint(0, 59), 
                                                        0, 0)
                        trip_start_time = start_time + added_time
                        trip_duration = self.get_trip_duration(gamma)
                        trip_end_time = trip_start_time + trip_duration
                        new_trip = data_model.Trip(str(random.randint(1,500)), "Casual", 2, trip_start_time, trip_end_time, start_station_id, end_station_id)
                        self.pending_departures.put((start_time, new_trip))
        print self.pending_departures.qsize()

    # This function should only be for testing, prints lambda counts for each year and hour given a weekend day in June
    def print_lambda_dict(self):
        for year in range(2010, 2015):
            month = 6
            is_week_day = False
            for hour in range(0,24):
                print year, month, hour, "--", len(self.lambda_distrs[year][month][is_week_day][hour])


    def predict_future_lambda(self, start_time, start_station_id, end_station_id):
        month = start_time.month
        slope = self.monthly_slope[month-1]
        intercept = self.monthly_intercept[month-1]
        lam_prediction = 0
        # TODO Delete prints
#        print "Month", month, "hour", start_time.hour
        for prev_year in self.get_year_range_of_data(month):
            prev_year_lambda = self.get_lambda(prev_year, month, start_time.weekday(), start_time.hour, start_station_id, end_station_id) 
#            print "Year", prev_year, ":", prev_year_lambda.value if prev_year_lambda else None
            if not prev_year_lambda: continue
#            else: print "Year", prev_year, ":", prev_year_lambda.value
#            prev_year_trips = slope * prev_year + intercept
#            future_year_trips = slope * start_time.year + intercept
#            lam_prediction += prev_year_lambda.value * future_year_trips / prev_year_trips
#            print "prev trips", prev_year_trips, "\t future trips", future_year_trips
            lam_prediction += self.log_predict_with_year_deltas(prev_year, prev_year_lambda, slope, intercept, start_time)
        lam_prediction /= len(self.get_year_range_of_data(month))
#        print "Prediction", lam_prediction
        if lam_prediction <= 0:
            return None
#        print "Prediction", lam_prediction
        return Lambda(start_station_id, end_station_id, start_time.hour, start_time.weekday()<5, start_time.year, month, lam_prediction)


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
        # Hopefully these are reasonable???
        prev_year_trips = slope * math.log(prev_year-2010+2) + intercept
        future_year_trips = slope * math.log(start_time.year-2010+2) + intercept
        lam_prediction = prev_year_lambda.value * future_year_trips / prev_year_trips
        return lam_prediction


    def get_year_range_of_data(self, month):
        #TODO: Don't just hard-code dates of existing data
        if month >= 10:
            return [2010, 2011, 2012]
        elif month <= 6:
            return [2011, 2012, 2013]
        else:
            return [2011, 2012]

    def avg_lambda(self, lam_list):
        # TODO this will underestimate the average because 2010 or 2013 may not have data
        return 1.0*sum(lam_list)/len(lam_list)


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
    
                month = start_time.month
                is_week_day = dow < 5
                
                lambda_poisson = self.session.query(data_model.Lambda) \
                    .filter(data_model.Lambda.is_week_day == is_week_day) \
                    .filter(data_model.Lambda.month == month) \
                    .filter(data_model.Lambda.hour.between(start_hour, end_hour))
  
                for lam in lambda_poisson:
#                    print num_added, ":", lam.year, month, lam.is_week_day, lam.hour, lam.value
                    distr_dict[lam.year][month][lam.is_week_day][lam.hour][(lam.start_station_id, lam.end_station_id)] = lam
                    num_added += 1


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
                                     .query(data_model.Lambda) \
                                     .filter(data_model.Lambda.month == month) \
                                     .filter(data_model.Lambda.year == year) \
                                     .filter(data_model.Lambda.is_week_day == is_week_day) \
                                     .filter(data_model.Lambda.hour.between(start_hour, end_hour))
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


if __name__ == '__main__':
    main()
