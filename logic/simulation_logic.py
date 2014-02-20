#!/usr/bin/env python
'''
    simulationLogic.py
'''
from utils import Connector
from models import * 
from sqlalchemy.sql import func, extract
import math
import bisect
import numpy
import Queue
import random
import datetime
import operator as op
# # Might need to move this to simulator eventually

DEPARTURE_TYPE = 0
ARRIVAL_TYPE = 1

class SimulationLogic:

    def __init__(self, session):
        # For database connectivity
        self.session = session
        # self.time is a datetime, representing the current time in the simulator.
        self.time = None

        # STATION STATES
        # s_id -> station object
        self.stations = {}
        # {stID : station's bike count at self.time}
        self.station_counts = {}
        # Another dictionary?! YES. Rather than accidentally mess up the 
        # capacities in the database we will store off capacities here.
        # Too easy for a commit to overwrite DB.
        self.station_caps = {}
        
        # Pending departures/arrivals includes tuples (endTime, trip)
        self.pending_departures = Queue.PriorityQueue()
        self.pending_arrivals = Queue.PriorityQueue()
        # Contains all resolved trips
        self.trip_list = []
        self.disappointments = []
        # List of trips that didn't end at the desired station due to a shortage
        self.bike_shortages = []
        self.dock_shortages = []

        # Max time which we allow a station to be empty/full
        self.rebalancing_time = None
        self.total_rebalances = 0
        # Keys: all currently empty/full station ids. Values: empty or full
        # Priority queue will allow us to designate how long a bike station remains unavailable
        self.full_stations = Queue.PriorityQueue()
        self.empty_stations = Queue.PriorityQueue()
        # Don't necessarily care which it is, just want to make sure we don't want 
        # to keep adding/removing it
        self.unavailable_stations = set()

        self.arr_dis_stations = {}
        self.dep_dis_stations = {}

        self.total_num_bikes = -1

    def getDBSession(self):
        return self.session

    def initialize(self, start_time, end_time, 
                    rebalancing_time=datetime.timedelta(seconds=1),
                    bike_total=None, station_caps={}, drop_stations=[]):
        '''
        Sets states of stations at the start_time
        '''
        print "Initializing"
        self.time = start_time

        self.start_time = start_time
        self.end_time = end_time
    
        # Stations should eventually be gotten from the database
        self.pending_departures = Queue.PriorityQueue()
        self.pending_arrivals = Queue.PriorityQueue()
        self.disappointment_list = []
        self.trip_list = []
        print "\tInitializing stations"
        self._initialize_stations(start_time, bike_total,
                                  station_caps, drop_stations)
        self._initialize_station_distances()
        # Defaults to instant rebalancing
        self.rebalancing_time = rebalancing_time

    def _get_total_num_bikes(self):
        '''
        Given a way to access the DB grab the max number of bikes at the stations
        that we've checked so far.
        '''
        # Check the days we have  and grab the largest count
        # provides a good upperbound on the total number of bikes
        max_bike_count= max(self.session.query(func.sum(StationStatus.bike_count))\
                .group_by(StationStatus.status_group_id).all())[0]
        return max_bike_count
     
    def _get_station_cap(self, s_id):
        return self.station_caps[s_id]

    def _initialize_station_distances(self, nearest=8):
        # Retrieve StationDistance objects representing the five closest
        # stations for each stations.
        self.nearest_station_dists = {}
        station_ids = self.stations.keys()

        for s_id in station_ids:
            nearest_distances = self.session.query(StationDistance)\
                    .filter(StationDistance.station1_id == s_id)\
                    .filter(StationDistance.station1_id.in_(station_ids))\
                    .filter(StationDistance.station2_id.in_(station_ids))\
                    .order_by(StationDistance.distance)[:8]
            self.nearest_station_dists[s_id] = nearest_distances


    def _initialize_stations(self, start_time, bike_total, 
                             station_caps, drop_stations):
        '''
        bike_total: Optional argument defining the number of bikes in the system.
            If none is supplied, takes Max from DB.
        station_caps: List of altered station caps. IMPORTANT: only stations 
            explicitely listed in station_caps will have capacity altered!
            {} != {31101:0}
        drop_stations: List of station ids that should be removed from the simulation
        '''
        # Only initialize bikes if nothing was supplied
        if not bike_total:
            bike_total = self._get_total_num_bikes()
        self.total_num_bikes = bike_total
        # Get the closest hour from current time
        start_hour = int(round(start_time.hour + start_time.minute/60.0))
        distributed_bikes = 0

        # For performance reasons don't do unnecessarily complex query if empty list
        if drop_stations:
            stations = self.session.query(Station)\
                                   .filter(~Station.id.in_(drop_stations))
        else:
            stations = self.session.query(Station)

        for s in stations:
            # Initialize capacity
            if s.id in station_caps:
                s_cap = station_caps[s.id]
            else:
                s_cap = s.capacity
            
            # Ignore stations with capacity of 0.
            #if s_cap < 1:
            #    print s.id, "has no capacity. Ignoring this station."

            # The cron_job now has hourly data (more or less)
            bike_counts = list(self.session.query(StationStatus.bike_count)\
                    .filter(StationStatus.station_id == s.id)\
                    .join(StatusGroup, aliased=True)\
                    .filter(extract('hour', StatusGroup.time) == start_hour))
            
            avg_count = numpy.average(bike_counts)
            std_count = numpy.std(bike_counts)

            if len(bike_counts) > 0:
                count = int(random.gauss(avg_count, std_count))
                if count > s_cap:
                    count = s_cap
                elif count < 0:
                    count = 0
            else:
                print 'Error initializing stations, unknown station'
                count = random.randint(0, s_cap)
            distributed_bikes += count
            self.stations[s.id] = s
            self.station_counts[s.id] = count
            self.station_caps[s.id] = s_cap
        
        bike_delta = bike_total - distributed_bikes

        # We need to distribute integer numbers (either pos or neg) so we need 
        # to sleect the correct function to distribute the greatest value from 0
        round_func = math.ceil
        if bike_delta < 0:
            round_func = math.floor
        
        # Don't keep trying to reassign bikes to full stations
        full_stations = set()
        while bike_delta > 0 and len(full_stations) < len(self.stations): 
            print "Init",bike_delta
            station_bike_prop = {s_id : float(s_count)/distributed_bikes 
                                    for s_id, s_count in self.station_counts.iteritems()
                                         if s_id not in full_stations}
            for s_id, prop in station_bike_prop.iteritems():
                added_bikes = round_func(prop * bike_delta) 
                s = self.stations[s_id]
                if added_bikes + self.station_counts[s.id] >= self._get_station_cap(s_id):
                    # Full station
                    if added_bikes == 0:
                        full_stations.add(s.id)
                    added_bikes = self._get_station_cap(s_id)  - self.station_counts[s.id]

                bike_delta -= added_bikes
                self.station_counts[s.id] += added_bikes

        if bike_delta > 0:
            print "WARNING: Number bikes exceed summed capacities across all stations"
    
        for s_id, s in self.stations.iteritems():
            if self._get_station_cap(s_id) <= self.station_counts[s_id]:
                print "\t\tFull station ",s_id, self._get_station_cap(s_id), self.station_counts[s.id]


    def update(self, timestep):
        '''Moves the simulation forward one timestep from given time'''
        self.generate_new_trips(self.time)
        self.time += timestep
        self.resolve_trips()

        
    def generate_new_trips(self, timestep):
        '''Generates trips COMPLETELY RANDOMLY WOOO'''
        for station in self.station_counts:
            num_trips = random.randint(0,self.station_counts[station])
            for i in range(num_trips):
                end_station_ID = random.choice(self.station_counts.keys())
                start_time = self.time + datetime.timedelta(minutes=random.randint(0, timestep.total_seconds()/60))
                # Nobody takes longer than 2 hours to bike anywhere, duh!
                end_time = start_time + datetime.timedelta(minutes=random.randint(0, 120))
                new_trip = data_model.Trip(str(random.randint(1,500)), "Casual", "Produced", start_time, end_time, station, end_station_ID)

                self.pending_departures.put((start_time, new_trip))


    def resolve_trips(self):
        '''Resolves departures & arrivals within the current time interval'''
        # Get the first event, be it a departure or arrival.
        eventTuple = self.get_first_trip_event()
        eventType = eventTuple[0]
        trip = eventTuple[1]
        while eventType != None:
            if self.rebalancing_time:
                # This is kind of gross, we just get the current time from the current trip...
                self.rebalance_stations(trip.start_date)
            if eventType == DEPARTURE_TYPE:
                if trip.start_date > self.time:
                    # Put trip back in proper queue if it's over the time, and stop the while loop
                    self.pending_departures.put((trip.start_date, trip))
                    break
                else:
                    self.resolve_departure(trip)
            elif eventType == ARRIVAL_TYPE:
                if trip.end_date > self.time:
                    self.pending_arrivals.put((trip.end_date, trip))
                    break
                else:
                    self.resolve_arrival(trip)
                    # print "If dock shortage, new trip is", printTrip(trip)

            eventTuple = self.get_first_trip_event()
            eventType = eventTuple[0]
            trip = eventTuple[1]
            
        
    def resolve_departure(self, trip):
        '''Decrement station count, put in pending_arrivals queue. If station is empty, put it in the disappointments list.'''
        departure_station_ID = trip.start_station_id

        if self.station_counts[departure_station_ID] == 0:
            new_disappointment = Disappointment(departure_station_ID, trip.start_date, trip_id=None)
            self.session.add(new_disappointment)
            if departure_station_ID not in self.dep_dis_stations:
                self.dep_dis_stations[departure_station_ID] = 1
            else:
                self.dep_dis_stations[departure_station_ID] += 1
            self.disappointment_list.append(new_disappointment)
            self.resolve_sad_departure(trip)
        else:
            self.station_counts[departure_station_ID] -= 1
            self.pending_arrivals.put((trip.end_date, trip))

            
    def resolve_sad_departure(self, trip):
        '''When you want a bike but the station is empty'''
        # Perfect time to denote a sad person
        if not trip.start_station_id in self.unavailable_stations:
            self.unavailable_stations.add(trip.start_station_id)
            self.empty_stations.put((trip.start_date, trip.start_station_id))



    def resolve_arrival(self, trip):
        '''Increment station count, put in trips list. If desired station is full, add a disappointment, set a new end station, and try again.'''
        arrival_station_ID = trip.end_station_id

        capacity = self._get_station_cap(arrival_station_ID)
        if self.station_counts[arrival_station_ID] == capacity:
            new_disappointment = Disappointment(arrival_station_ID, trip.end_date, trip_id=None)
            trip.disappointments.append(new_disappointment)
            if arrival_station_ID not in self.arr_dis_stations:
                self.arr_dis_stations[arrival_station_ID] = 1
            else:
                self.arr_dis_stations[arrival_station_ID] += 1
            self.disappointment_list.append(new_disappointment)
            self.resolve_sad_arrival(trip)
        else:
            self.station_counts[arrival_station_ID] += 1
            self.trip_list.append(trip)


    def resolve_sad_arrival(self, trip):
        '''When you want to drop off a bike but the station is full'''
        # Perfect time to denote a sad person
        if not trip.end_station_id in self.unavailable_stations:
            self.unavailable_stations.add(trip.end_station_id)
            self.full_stations.put((trip.end_date, trip.end_station_id))

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

    def get_first_trip_event(self):
        '''Returns a tuple for the first departure or arrival's trip including (type of event, trip). Type of event is either departure, arrival, or None.'''
        if self.pending_departures.empty() and self.pending_arrivals.empty():
            trip = None
            eventType = None
        elif self.pending_arrivals.empty():
            trip = self.pending_departures.get()[1]
            eventType = DEPARTURE_TYPE
        elif self.pending_departures.empty():
            trip = self.pending_arrivals.get()[1]
            eventType = ARRIVAL_TYPE
        else:
            first_departure = self.pending_departures.get()[1]
            first_arrival = self.pending_arrivals.get()[1]
            # If a departure and arrival happen at the exact same time, departures resolve first. This decision was completely arbitrary.
            if (first_departure.start_date <= first_arrival.end_date):
                trip = first_departure
                eventType = DEPARTURE_TYPE
                self.pending_arrivals.put((first_arrival.end_date, first_arrival))
            else:
                trip = first_arrival
                eventType = ARRIVAL_TYPE
                self.pending_departures.put((first_departure.start_date, first_departure))
        return (eventType, trip)

    def rebalance_stations(self, cur_time):		
        # Check to see if anything has exceeded that time
        # NOTE: potential error, if you have a rebalance time < 1 hour 
        # could potentially exceed that time

        #TODO: peak->.queue
        continue_removing = True
        while not self.full_stations.empty() and continue_removing:
            time, s_id  = self.full_stations.get()
            if cur_time - time >= self.rebalancing_time:
                to_remove = self._get_station_cap(s_id)/2
                self.station_counts[s_id] -= to_remove
                self.moving_bikes += to_remove
                self.total_rebalances += to_remove
                self.unavailable_stations.remove(s_id)
            else:
                continue_removing = False
                self.full_stations.put((time, s_id))

        # If there are empty stations that are empty add to them
        need_bikes = []
        continue_removing = True
        while not self.empty_stations.empty() and continue_removing:
            time, s_id = self.empty_stations.get()
            if cur_time - time >= self.rebalancing_time:
                need_bikes.append(s_id)
            else:
                continue_removing = False
                self.empty_stations.put((time, s_id))

        crowded_stations = sorted(self.stations,
            key=lambda x: self._get_station_cap(x) - self.station_counts[x])
        i = 0 
        # If any of the stations are fuller than others take from them
        # Also we'll give every station more than 1 bike
        while self.moving_bikes < len(need_bikes) * 5:
            s_id = crowded_stations[i]
            i += 1
            to_remove = self.station_counts[s_id] - self._get_station_cap(s_id) / 2
            #print "count, cap", self.station_counts[s_id], self._get_station_cap(s_id) / 2
            if to_remove < 0:
                # Try removing to down to less than half
                if self.station_counts[s_id] > 2:
                    to_remove = self.station_counts[s_id] / 2
                else:
                    break

            self.station_counts[s_id] -= to_remove
            self.moving_bikes += to_remove
            self.total_rebalances += to_remove
       
        if len(need_bikes) > 0:
            bikes_to_distr = self.moving_bikes / len(need_bikes) 
            for s_id in need_bikes:
                self.station_counts[s_id] += bikes_to_distr
                self.unavailable_stations.remove(s_id)


    def flush(self):
        '''Returns list of all trips since initialization, or adds them to the database if to_database is True'''

        return {'trips':self.trip_list,
                'disappointments':self.disappointment_list,
                'arr_dis_stations':self.arr_dis_stations,
                'dep_dis_stations':self.dep_dis_stations,
                'total_rebalances':self.total_rebalances,
                'total_num_bikes':self.total_num_bikes}
        

    def cleanup(self):
        pass

def main():
    conn = Connector()
    sess = conn.getDBSession()

    SL = SimulationLogic(sess)
    start_time = datetime.datetime(2013, 1, 1, 0, 0, 0)
    SL.initialize(start_time)
    step = datetime.timedelta(minutes=30)
    SL.update(step)
    SL.update(step)
    trips = SL.flush()
      

if __name__ == "__main__":
    main()
