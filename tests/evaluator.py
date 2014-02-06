#!/usr/bin/python
'''
A class for comparing the trips our simulator generates to real trips.
'''

from scipy.stats import chisquare
import numpy
import datetime
import sys

from models import *
from utils import Connector
from logic import *

class Evaluator:
    '''
    Running one chi-square test for the entirety of a simulation's results:
        1) evaluator = Evaluator(<session>, <granularity>, <start_date>, <end_date>, <prod_trips>, <prod_on_start>, <prod_on_end>)
        2) results = evaluator.run_chi_square(<statistic>)
        3) chi_sq = results[0]
        4) p_valu = results[1]
    '''
    def __init__(self,session,granularity,start_date,end_date,prod_trips=None,prod_on_start=None,prod_on_end=None):
        self.session = session
        self.granularity = granularity
        self.start_date = start_date
        self.end_date = end_date
        self.day_range = self.get_day_range()
        self.prod_trips = self.get_prod_trips(prod_trips,prod_on_start,prod_on_end)
        self.stations = self.session.query(Station)
        self.day_counts = None
        self.day = None

    def get_day_range(self):
        print "Getting day range:",
        start_day = self.start_date.isoweekday()
        end_day = self.end_date.isoweekday()

        if start_day - end_day == 0:
            day_range = [start_day]
        elif start_day - end_day < 0:
            day_range = range(start_day,end_day+1)
        else:
            day_range = range(start_day,8) + range(1,end_day+1)
        print day_range
        return day_range

    def get_day_counts(self):
        dates = []
        day_counts = [0,0,0,0,0,0,0]
        for trip in self.real_trips:
            date = trip[0]
            simple_date = datetime.datetime(date.year,date.month,date.day)
            if simple_date not in dates:
                dates.append(simple_date)
        for date in dates:
            day_counts[date.isoweekday()-1] += 1

        print 'day_counts:',day_counts
        return day_counts

    def get_real_trips(self):
        print "Fetching real trips from database for day %d." % self.day
        
        real_trips = []

        if self.day == 7:
            day = 0
        else:
            day = self.day

        c = Connector()
        engine = c.getDBEngine()
        query = "select id as t_id, start_station_id as s_id, end_station_id as e_id, start_date, end_date \
                from (select *, extract(dow from start_date) as dow from trips) as s1 where dow = %d;" % day
        results = engine.execute(query)
        
        print "Real trips fetched. Processing trips."
        
        row_counter = 0
        
        for row in results:
            row_counter += 1
            t_id = row["t_id"]
            start_date = row["start_date"]
            end_date = row["end_date"]
            s_id = row["s_id"]
            e_id = row["e_id"]
            real_trips.append((start_date,end_date,s_id,e_id,t_id))
        
        print 'Processed %d trips.' % row_counter
        return real_trips
        
    def get_prod_trips(self,prods,prod_on_start,prod_on_end):
        if prods:
            prod_trips = prods
        else:
            prod_trips = self.session.query(Trip) \
                .filter(Trip.start_date.between(self.start_date,self.end_date)) \
                .join(Trip.trip_type, aliased=True) \
                .filter(TripType.trip_type == 'Produced')\
                .filter(TripType.produced_on.between(prod_on_start,prod_on_end))
        return prod_trips
    
    def setup_single_stations(self):
        time_travel_counter = 0
        trips = []

        for trip in self.real_trips:
            trips.append(trip)
        
        for trip in self.prod_trips:
            trips.append(trip)

        single_stations = {}
        
        for station in self.stations:
            single_stations[station.id] = SingleStation(station.id,self.granularity)

        for trip in trips:
            if type(trip) == tuple:
                trip_id = trip[-1]

                day = trip[0].isoweekday() - 1

                start_station = trip[2]
                end_station = trip[3]

                start_hour = trip[0].hour
                end_hour = trip[1].hour
                
                dur_delta = trip[1] - trip[0]
                trip_duration = dur_delta.total_seconds()

            else:
                day = trip.start_date.isoweekday() - 1
            
                start_station = trip.start_station_id
                end_station = trip.end_station_id
            
                start_hour = trip.start_date.hour
                end_hour = trip.end_date.hour

                trip_duration = trip.duration().total_seconds()
            
            if end_hour < start_hour and start_hour - end_hour < 20:
                #print 'WARNING! Time-traveler: start_hour: %d, end_hour: %d' % (start_hour, end_hour)
                time_travel_counter += 1
            
            if self.granularity == 'hours':
                if type(trip) == tuple:
                    single_stations[start_station].real_departures[day][start_hour] += 1
                    single_stations[end_station].real_arrivals[day][end_hour] += 1
                    single_stations[start_station].real_durations[day][start_hour][0] += 1
                    single_stations[start_station].real_durations[day][start_hour][1] += trip_duration
                else:
                    single_stations[start_station].prod_departures[day][start_hour] += 1
                    single_stations[end_station].prod_arrivals[day][end_hour] += 1
                    single_stations[start_station].prod_durations[day][start_hour][0] += 1
                    single_stations[start_station].prod_durations[day][start_hour][1] += trip_duration
            elif self.granularity == 'days':
                if type(trip) == tuple:
                    single_stations[start_station].real_departures[day] += 1
                    single_stations[end_station].real_arrivals[day] += 1
                    single_stations[start_station].real_durations[day][0] += 1
                    single_stations[start_station].real_durations[day][1] += trip_duration
                else:
                    single_stations[start_station].prod_departures[day] += 1
                    single_stations[end_station].prod_arrivals[day] += 1
                    single_stations[start_station].prod_durations[day][0] += 1
                    single_stations[start_station].prod_durations[day][1] += trip_duration
        
        print 'time_travel_counter', time_travel_counter    
        return single_stations
    
    def run_manhattan(self,statistic,day):
        over_productions = 0
        under_productions = 0
        perfections = 0

        if day != self.day:
            self.day = day
            self.real_trips = self.get_real_trips()
            self.single_stations = self.setup_single_stations()
            self.day_counts = self.get_day_counts()

        for station_id, station_obj in self.single_stations.iteritems():
            if self.granularity == 'days':
                if statistic == 'departures':
                    real_trips = station_obj.real_departures[day-1] / float(self.day_counts[self.day - 1])
                    prod_trips = station_obj.prod_departures[day-1]
                    man_dist = real_trips - prod_trips

                    if man_dist > 0:
                        under_productions += 1
                        label = 'under-produced'
                    elif man_dist < 0:
                        over_productions += 1
                        label = 'over-produced'
                    else:
                        perfections += 1
                        label = 'just right!'

                    print '%d | %10f | %15s' % (station_id,man_dist,label)
            
            elif self.granularity == 'hours':
                for hour in range(24):
                    real_trips = station_obj.real_departures[day-1][hour] / float(self.day_counts[day-1])
                    prod_trips = station_obj.prod_departures[day-1][hour]
                    man_dist = real_trips - prod_trips
                    print '%d | %d | %f' % (station_id,hour,man_dist)
        print 'Too many:', over_productions
        print 'Too few: ', under_productions
        print 'Perfect: ', perfections

    def run_chi_square(self,statistic,day):
        if day != self.day:
            self.day = day
            self.real_trips = self.get_real_trips()
            self.single_stations = self.setup_single_stations()
            self.day_counts = self.get_day_counts()
        
        print 'Starting chi-square test.'
        low_observed_freqs = 0
        low_expected_freqs = 0
        zero_count = 0
        observed = []
        expected = []

        for station_id, station_obj in self.single_stations.iteritems():
            station_obs = []
            station_exp = []
            
            if self.granularity == 'days':
                if statistic == 'departures':
                    new_observed = station_obj.prod_departures[day-1]
                    new_expected = station_obj.real_departures[day-1] / float(self.day_counts[day-1])
                elif statistic == 'arrivals':
                    new_observed = station_obj.prod_arrivals[day-1]
                    new_expected = station_obj.real_arrivals[day-1] / float(self.day_counts[day-1])
                elif statistic == 'durations':
                    num_prod_trips = station_obj.prod_durations[day-1][0]
                    prod_durations = station_obj.prod_durations[day-1][1]
                    if num_prod_trips == 0:
                        num_prod_trips = 1
                    avg_prod_duration = prod_durations / float(num_prod_trips)

                    num_real_trips = station_obj.real_durations[day-1][0]
                    real_durations = station_obj.real_durations[day-1][1]
                    if num_real_trips == 0:
                        num_real_trips = 1
                    avg_real_duration = real_durations / float(num_real_trips)

                    new_observed = avg_prod_duration
                    new_expected = avg_real_duration
                else:
                    print 'ERROR: Unknown statistic used in chi-square test.'
                    return

                if new_expected < 1:
                    zero_count += 1
                    new_expected = 1
                    
                observed.append(new_observed)
                expected.append(new_expected)

                station_obs.append(new_observed)
                station_exp.append(new_expected)
                    
                print "%d   | %d   | %f        | %d        | %s" % (station_id,day,new_expected,new_observed,statistic)

                if new_observed < 5:
                    low_observed_freqs += 1
                if new_expected < 5:
                    low_expected_freqs += 1

            elif self.granularity == 'hours':
                print "--------------------------------------------------------"
                print 'Chi-Square: Working on station', station_id
                print "--------------------------------------------------------"
                print "Station | Day | Hour | Expected | Observed | Statistic"
                print "--------------------------------------------------------"
                
                for hour in range(24):
                    if statistic == 'departures':
                        new_observed = station_obj.prod_departures[day-1][hour]
                        new_expected = station_obj.real_departures[day-1][hour] / float(day_counts[day-1])
                   
                    elif statistic == 'arrivals':
                        new_observed = station_obj.prod_arrivals[day-1][hour]
                        new_expected = station_obj.real_arrivals[day-1][hour] / float(day_counts[day-1])
                   
                    elif statistic == 'durations':
                        num_prod_trips = station_obj.prod_durations[day-1][hour][0]
                        prod_durations = station_obj.prod_durations[day-1][hour][1]
                        if num_prod_trips == 0:
                            num_prod_trips = 1
                        avg_prod_duration = prod_durations / float(num_prod_trips)

                        num_real_trips = station_obj.real_durations[day-1][hour][0]
                        real_durations = station_obj.real_durations[day-1][hour][1]
                        if num_real_trips == 0:
                            num_real_trips = 1
                        avg_real_duration = real_durations / float(num_real_trips)

                        new_observed = avg_prod_duration
                        new_expected = avg_real_duration
                   
                    else:
                        print 'ERROR: Unknown statistic used in chi-square test.'
                        return
                   
                    if new_expected < 1:
                        zero_count += 1
                        new_expected = 1
                    
                    observed.append(new_observed)
                    expected.append(new_expected)

                    station_obs.append(new_observed)
                    station_exp.append(new_expected)
                    
                    if len(str(hour)) == 1:
                        print "%d   | %d   | %d    | %f        | %d        | %s" % (station_id,day,hour,new_expected,new_observed,statistic)
                    else:
                        print "%d   | %d   | %d   | %f        | %d        | %s" % (station_id,day,hour,new_expected,new_observed,statistic)

                    if new_observed < 5:
                        low_observed_freqs += 1
                    if new_expected < 5:
                        low_expected_freqs += 1
            
            if self.granularity == 'hours':
                station_chi_sq = chisquare(numpy.asarray(station_obs),numpy.asarray(station_exp))
                print "--------------------------------------------------------"
                print 'Chi-Square = %f   p-value = %f' % (station_chi_sq[0],station_chi_sq[1])

        print 'observed_freqs < 5:', low_observed_freqs
        print 'expected_freqs < 5:', low_expected_freqs
        print 'expected_freqs = 0:', zero_count

        return chisquare(numpy.asarray(observed),numpy.asarray(expected))
 
class SingleStation:
    def __init__(self,id,granularity='hours'):
        self.id = id
        
        if granularity == 'days':
            self.real_departures = [0 for x in range(7)]
            self.real_arrivals = [0 for x in range(7)]
            self.real_durations = [[0,0] for x in range(7)]
            
            self.prod_departures = [0 for x in range(7)]
            self.prod_arrivals = [0 for x in range(7)]
            self.prod_durations = [[0,0] for x in range(7)]
        elif granularity == 'hours':
            self.real_departures = [[0 for x in range(24)] for x in range(7)]
            self.real_arrivals = [[0 for x in range(24)] for x in range(7)]
            self.real_durations = [[[0,0] for x in range(24)] for x in range(7)]
            
            self.prod_departures = [[0 for x in range(24)] for x in range(7)]
            self.prod_arrivals = [[0 for x in range(24)] for x in range(7)]
            self.prod_durations = [[[0,0] for x in range(24)] for x in range(7)]

def print_usage():
    print '\nUSAGE'
    print '--> python evaluator.py <granularity> <start_date> <end_date> <prod_trips> <prod_on_start> <prod_on_end>'
    print "--> Valid statistics are 'departures', 'arrivals', and 'durations'."
    print "--> Format dates as '%Y-%m-%d'.\n"
            
def main():
    statistics = ['departures','arrivals','durations']
    granularities = ['days','hours']
    session = Connector().getDBSession()
    
    if len(sys.argv) == 1:
        print 'Using default values.'
        
        granularity = 'days'

        start_date = datetime.datetime.strptime("2012-7-1 00 00", '%Y-%m-%d %H %M')
        end_date = datetime.datetime.strptime("2012-7-1 23 59", '%Y-%m-%d %H %M')
        
        logic = ExponentialLogic(session)
        simulator = Simulator(logic)
        results = simulator.run(start_date, end_date)

        prod_on_start = None #datetime.datetime.utcnow() - datetime.timedelta(days=30)
        prod_on_end =  None #datetime.datetime.utcnow()
        
    else:
        if len(sys.argv) < 5 or sys.argv[1] not in statistics:
            print_usage()
            return
        
        granularity = sys.argv[1]
        start_date = datetime.datetime.strptime(sys.argv[2], '%Y-%m-%d')
        end_date = datetime.datetime.strptime(sys.argv[3], '%Y-%m-%d')
        prod_on_start = datetime.datetime.strptime(sys.argv[4], '%Y-%m-%d')
        prod_on_end = datetime.datetime.strptime(sys.argv[5], '%Y-%m-%d')
    
    print 'produced trips:', len(results["trips"])
    evaluator = Evaluator(session,granularity,start_date,end_date,results["trips"],prod_on_start,prod_on_end)
    
    for day in evaluator.day_range:
        evaluator.run_manhattan('departures',day)

    #for day in evaluator.day_range:
    #    result = evaluator.run_chi_square('departures',day)
    #    chi_sq = result[0]
    #    p_valu = result[1]
    #    print 'chi square = ', chi_sq
    #    print 'p value = ', p_valu
            
if __name__ == '__main__':
    main()

    #def setup_paired_stations(self,trips,stations):
    #    paired_stations = {}
    #    for start in stations:
    #        for end in stations:
    #            if (start.id,end.id) not in station_pairs:
    #                station_pairs[(start.id,end.id)] = StationPair(start,end)
    #    for trip in trips:
    #        start = trip.start_station_id
    #        end = trip.end_station_id
    #        if (start.id,end.id) not in station_pairs:
    #            new_station_pair = StationPair(start,end)
    #            new_station_pair.add_trip(trip)
    #            paired_stations[(start.id,end.id)] = new_station_pair
    #        else:
    #            paired_stations[(start.id,end.id)].add_trip(trip)
    #    return paired_stations
    
    #def compare_trip_numbers(self,station_pair):
    #    num_real_trips = len(station_pair.real_trips)
    #    num_prod_trips = len(station_pair.prod_trips)
    #    return num_real_trips - num_prod_trips
    
    #def compare_trip_times(self,station_pair):
    #    total_real_time = 0
    #    total_prod_time = 0
    #    for trip in station_pair.real_trips:
    #        total_real_time += trip.duration()
    #    for trip in station_pair.prod_trips:
    #        total_prod_time += trip.duration()
    #    avg_real_time = total_real_time / len(station_pair.real_trips)
    #    avg_prod_time = total_prod_time / len(station_pair.prod_trips)
    #    return avg_real_time - avg_prod_time

# class StationPair:
#     def __init__(self,start_station,end_station):
#         self.start_station = start_station
#         self.end_station = end_station
#         self.real_trips = []
#         self.prod_trips = []
#     
#     def add_trip(self,trip):
#         if trip.trip_type == 'Testing':
#             self.real_trips.append(trip)
#         elif trip.trip_type == 'Produced':
#             self.prod_trips.append(trip)
#         else:
#             print "Error: station_pair trips must be of type 'Testing' or 'Produced'."

# Originally methods in SingleStation
        # def compare_departure_numbers(self,day):
        #     num_real_departures = self.real_departures[day][hour]
        #     num_prod_departures = self.prod_departures[day][hour]
        #     return num_real_departures - num_prod_departures
            
        # def compare_arrival_numbers(self,day):
        #     num_real_arrivals = self.real_arrivals[day][hour]
        #     num_prod_arrivals = self.prod_arrivals[day][hour]
        #     return num_real_arrivals - num_prod_arrivals
            
        # def compare_avg_durations(self,day):
        #     real_avg = self.real_durations[day][1] / float(self.real_durations[day][0])
        #     prod_avg = self.prod_durations[day][1] / float(self.prod_durations[day][0])
        #     return real_avg - prod_avg
