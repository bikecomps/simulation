#!/usr/bin/python
'''
A class for comparing the trips our simulator generates to real trips.
'''

from utils import Connector
<<<<<<< HEAD
from scipy.stats import chisquare
import datetime
import sys
=======
>>>>>>> c8d8d0f87cce897f35a01d89bc1b3ccf9b39061d

class Evaluator:
    def __init__(self,session,statistic,start_date,end_date,prod_on_start,prod_on_end):
        self.session = session
        self.trips = self.get_trips(start_date,end_date,prod_on_start,prod_on_end)
        self.stations = self.session.query(Station)
        self.single_stations = self.setup_single_stations(self.trips,self.stations)
        #self.paired_stations = self.setup_paired_stations(self.trips,self.stations)
    
    def get_trips(self,trips_start,trips_end,prod_on_start,prod_on_end):
    	# Note: Currently using 'Training' trips rather than 'Testing' trips.
    	trips = session.query(Trip) \
            .filter(Trip.trip_type.trip_type == 'Produced' or Trip.trip_type.trip_type == 'Training') \
            .filter(Trip.start_date.between(trip_start_date,trip_end_date)) \
            .filter(Trip.trip_type.produced_on.between(prod_on_start,prod_on_end))
        return trips
    
    def setup_single_stations(self,trips,stations):
        single_stations = {}
        
        for station in stations:
            if station in single_stations:
                print 'Error: Found a duplicate station ID.'
            else:
                single_stations[station.id] = SingleStation(station.id)
        
        for trip in trips:
            day = trip.start_date.isoweekday()
            
            start_station = trip.start_station_id
            end_station = trip.end_station_id
            
            start_hour = trip.start_date.hour
            end_hour = trip.end_date.hour
            
            if end_hour < start_hour:
                print 'WARNING: Found trip with end_hour that precedes start_hour.'
                print 'Time-Traveling Trip: ', trip.id
            
            # Using 'Training' until we have 'Testing' trips in DB.
            if trip.trip_type.trip_type == "Training":
                single_stations[start_station].real_departures[day][start_hour] += 1
                single_stations[end_station].real_arrivals[day][end_hour] += 1
                single_stations[start_station].real_durations[day][start_hour][0] += 1
                single_stations[start_station].real_durations[day][start_hour][1] += trip.duration()
                
            elif trip.trip_type.trip_type == "Produced":
                single_stations[start_station].prod_departures[day][start_hour] += 1
                single_stations[end_station].prod_arrivals[day][end_hour] += 1
                single_stations[start_station].prod_durations[day][start_hour][0] += 1
                single_stations[start_station].prod_durations[day][start_hour][1] += trip.duration()
            
        return single_stations
        
    def setup_paired_stations(self,trips,stations):
        paired_stations = {}
        for start in stations:
            for end in stations:
                if (start.id,end.id) not in station_pairs:
                    station_pairs[(start.id,end.id)] = StationPair(start,end)
        for trip in trips:
            start = trip.start_station_id
            end = trip.end_station_id
            if (start.id,end.id) not in station_pairs:
                new_station_pair = StationPair(start,end)
                new_station_pair.add_trip(trip)
                paired_stations[(start.id,end.id)] = new_station_pair
            else:
                paired_stations[(start.id,end.id)].add_trip(trip)
        return paired_stations
    
    def compare_all_departure_numbers(self):
        print '-'*60, '\nComparing departure numbers for all single stations.\n', '-'*60
        for station in self.single_stations:
            print 'Comparing departure numbers for station ', station.id
            for day in range(1,8):
                for hour in range(24):
                    difference = station.compare_departure_numbers(day,hour)
                    print "[Station:%d, Day:%d, Hour:%d] Difference in Departures: %d" \
                        % (station.id,day,hour,difference)
    
    def compare_all_arrival_numbers(self):
        print '-'*60, '\nComparing arrival numbers for all single stations.\n', '-'*60
        for station in self.single_stations:
            print 'Comparing arrival numbers for station ', station.id
            for day in range(1,8):
                for hour in range(24):
                    difference = station.compare_arrival_numbers(day,hour)
                    print "[Station:%d, Day:%d, Hour:%d] Difference in Arrivals: %d" \
                        % (station.id,day,hour,difference)
    
    def compare_all_avg_trip_times(self):
        print '-'*60, '\nComparing average durations for all single stations.\n', '-'*60
        for station in self.single_stations:
            print 'Comparing average durations for trips starting at station ', station.id
            for day in range(1,8):
                for hour in range(24):
                    difference = station.compare_avg_durations(day,hour)
                    print "[Station:%d, Day:%d, Hour:%d] Difference in Durations: %d" \
                        % (station.id,day,hour,difference)
    
    def check_expected_freqs(self,statistic):
        for station in self.single_stations:
            for day in range(1,8):
                for hour in range(24):
                    expected_freq = station.statistic[day][hour] # THIS IS WRONG!
                    if expected_freq < 5:
                        print 'ERROR: %s for station $d: %d.' \
                               % (statistic,station.id,expected_freqs)
                        #return False
        #print 'All expected values were greater than 5. Chi-Squared test approved.'
        #return True
    
    def calculate_chi_square(self):
        print 'Beginning chi-square test for goodness of fit.'
        observed = []
        expected = []
        
        for station in self.single_stations:
            print 'Chi-Square: Working on station ', station.id
            for day in range(1,8):
                for hour in range(24):
                    if self.statistic == 'departures':
                        new_observed = station.prod_departures[day][hour]
                        new_expected = station.real_departures[day][hour]
                    
                    elif self.statistic == 'arrivals':
                        new_observed = station.prod_arrivals[day][hour]
                        new_expected = station.real_arrivals[day][hour]
                    
                    elif self.statistic == 'durations':
                        new_observed = station.prod_durations[day][hour]
                        new_expected = station.real_durations[day][hour]
                    
                    else:
                        print 'ERROR: Unknown statistic used in chi-square test for g-o-f.'
                        return
                    
                    observed.append(new_observed)
                    expected.append(new_expected)
                    
                    print "[Station:%d, Day:%d, Hour:%d] Observed %s: %d" \
                        % (station.id,day,hour,statistic,new_observed)
                    
                    print "[Station:%d, Day:%d, Hour:%d] Expected %s: %d" \
                        % (station.id,day,hour,statistic,new_expected)
        
        return chisquare(observed,expected)
    
    # Outdated, from when focus was on pairwise stats.
    def compare_trip_numbers(self,station_pair):
        num_real_trips = len(station_pair.real_trips)
        num_prod_trips = len(station_pair.prod_trips)
        return num_real_trips - num_prod_trips
    
    # Outdated, from when focus was on pairwise stats.    
    def compare_trip_times(self,station_pair):
        total_real_time = 0
        total_prod_time = 0
        for trip in station_pair.real_trips:
            total_real_time += trip.duration()
        for trip in station_pair.prod_trips:
            total_prod_time += trip.duration()
        avg_real_time = total_real_time / len(station_pair.real_trips)
        avg_prod_time = total_prod_time / len(station_pair.prod_trips)
        return avg_real_time - avg_prod_time
 
class SingleStation:
    def __init__(self,id):
        self.id = id
        
        self.real_departures = [[0] * 24] * 7
        self.real_arrivals = [[0] * 24] * 7
        self.real_durations = [[(0,0)] * 24] * 7
        
        self.prod_departures = [[0] * 24] * 7
        self.prod_arrivals = [[0] * 24] * 7
        self.prod_durations = [[(0,0)] * 24] * 7
        
        def compare_departure_numbers(self,day,hour):
            num_real_departures = self.real_departures[day][hour]
            num_prod_departures = self.prod_departures[day][hour]
            return num_real_departures - num_prod_departures
            
        def compare_arrival_numbers(self,day,hour):
            num_real_arrivals = self.real_arrivals[day][hour]
            num_prod_arrivals = self.prod_arrivals[day][hour]
            return num_real_arrivals - num_prod_arrivals
            
        def compare_avg_durations(self,day,hour):
            real_avg = self.real_durations[day][hour][1] / float(self.real_durations[day][hour][0])
            prod_avg = self.prod_durations[day][hour][1] / float(self.prod_durations[day][hour][0])
            return real_avg - prod_avg
            
class StationPair:
    def __init__(self,start_station,end_station):
        self.start_station = start_station
        self.end_station = end_station
        self.real_trips = []
        self.prod_trips = []
    
    def add_trip(self,trip):
        if trip.trip_type == 'Testing':
            self.real_trips.append(trip)
        elif trip.trip_type == 'Produced':
            self.prod_trips.append(trip)
        else:
            print "Error: station_pair trips must be of type 'Testing' or 'Produced'."

def print_usage():
    print '\nUSAGE'
    print '--> python evaluator.py <statistic> <start_date> <end_date> <prod_on_start> <prod_on_end>'
    print "--> Valid statistics are 'departures', 'arrivals', and 'durations'."
    print "--> Format dates as '%Y-%m-%d'.\n"
            
def main():
    statistics = ['departures', 'arrivals','durations']
    
    if len(sys.argv) == 1:
        # defaults
        print 'Using default values.'
        
        statistic = 'departures'
        start_date = datetime.datetime.strptime("2012-6-1", '%Y-%m-%d')
        end_date = datetime.datetime.strptime("2012-6-2", '%Y-%m-%d')
        prod_on_start = datetime.datetime.now() - datetime.timedelta(days=1)
        prod_on_end = datetime.datetime.now() # Should this be .utcnow()?
    
    else:
        if len(sys.argv) < 6 or sys.argv[1] not in statistics:
            print_usage()
            return
        
        statistic = sys.argv[1]
        start_date = datetime.datetime.strptime(sys.argv[2], '%Y-%m-%d')
        end_date = datetime.datetime.strptime(sys.argv[3], '%Y-%m-%d')
        prod_on_start = datetime.datetime.strptime(sys.argv[4], '%Y-%m-%d')
        prod_on_end = datetime.datetime.strptime(sys.argv[5], '%Y-%m-%d')
    
	#session = Connector().getDBSession()
    #evaluator = Evaluator(session,statistic,start_date,end_date,prod_on_start,prod_on_end)
    #evaluator.calculate_chi_square()
    
    #for pair in evaluator.station_pairs:
        #NOTE: Encapsulate the section below into a method in Evaluator.
        #NOTE: It could be helpful to note particularly high or low differences.
        #num_diff = evaluator.compare_trip_numbers(pair)
        #if num_diff > 0:
        #    print 'pair %s generated %d fewer trips than reality.' % (pair, num_diff)
        #elif num_diff < 0:
        #    print 'pair %s generated %d more trips than reality.' % (pair, num_diff)
        #else:
        #    print 'pair %s generated the real number of trips!' % pair
            
if __name__ == '__main__':
    main()
