#!/usr/bin/python
'''
A class for comparing the trips our simulator generates to real trips.
'''

from utils import Connector

class Evaluator:
    def __init__(self):
        self.trips = self.get_trips()
        self.station_pairs = self.setup_station_pairs(self.trips)
    
    def compare_trip_numbers(self,station_pair):
        num_real_trips = len(station_pair.real_trips)
        num_prod_trips = len(station_pair.prod_trips)
        return num_real_trips - num_prod_trips
        
    def compare_avg_trip_times(self,station_pair):
        total_real_trip_time = 0
        total_prod_trip_time = 0
        for trip in station_pair.real_trips:
            trip_length = trip.trip_length # how should this be calculated?
            total_real_trip_time += trip_length
        for trip in station_pair.prod_trips:
            trip_length = trip.trip_length # how should this be calculated?
            total_prod_trip_time += trip_length
        avg_real_trip_time = total_real_trip_time / len(station_pair.real_trips)
        avg_prod_trip_time = total_prod_trip_time / len(station_pair.prod_trips)
        return avg_real_trip_time - avg_prod_trip_time
        
    def setup_station_pairs(self,trips):
        station_pairs = {}
        for trip in trips:
            start = trip.start_station_id
            end = trip.end_station_id
            if (start,end) not in station_pairs:
                new_station_pair = StationPair(start,end)
                new_station_pair.add_trip(trip)
                station_pairs[(start,end)] = new_station_pair
            else:
                station_pairs[(start,end)].add_trip(trip)
        return station_pairs
    
    def get_trips(self,start_time,end_time):
        c = Connector()
		session = c.getDBSession()
    	engine = c.getDBEngine()
    	trips = session.query(Trip) \
            # Will the filter below work?
            .filter(Trip.trip_type == 'Produced' or Trip.trip_type == 'Testing') \
            .filter(Trip.start_date.between(start_date, end_date)) \
            .yield_per(cap)
        return trips
        
class StationPair:
    def __init__(self,start,end):
        self.start_station = start
        self.end_station = end
        self.real_trips = []
        self.prod_trips = []
    
    def add_trip(self,trip):
        if trip.trip_type == 'Testing':
            self.real_trips.append(trip)
        elif trip.trip_type == 'Produced':
            self.prodTrips.append(trip)
        else:
            print "Error: station_pair trips must be of type 'Testing' or 'Produced'."
            
def main():
    evaluator = Evaluator()
    for pair in evaluator.station_pairs:
        # NOTE: Encapsulate the section below into a method in Evaluator.
        # NOTE: It could be helpful to note particularly high or low differences.
        num_diff = evaluator.compare_trip_numbers(pair)
        if num_diff > 0:
            print 'station_pair %s generated %d fewer trips than reality.' % (pair, num_diff)
        elif num_diff < 0:
            print 'station_pair %s generated %d more trips than reality.' % (pair, num_diff)
        else:
            print 'station_pair %s generated exactly the real number of trips!' % pair
    
    # NOTE: Consider encapsulating the section below into a method in Evaluator.
    #for pair in evaluator.station_pairs:
    #    avgDiff = evaluator.compare_avg_trip_times(pair)
    #    if avgDiff > 0:
    #        print 'foo'
    #    elif avgDiff < 0:
    #        print 'bar'
    #    else:
    #        print 'baz'
            
if __name__ == '__main__':
    main()
