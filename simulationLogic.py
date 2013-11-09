'''
    simulationLogic.py
'''
from utility import Connector
import data_model
import Queue
import random
import datetime
# # Might need to move this to simulator eventually
import hidden
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
DEPARTURE_TYPE = 0
ARRIVAL_TYPE = 1

class SimulationLogic:

    def __init__(self, session):
        # For database connectivity
        self.session = session
        # self.time is a datetime, representing the current time in the simulator.
        self.time = None
        # {stID : station's bike count at self.time}
        self.stations = {}
        # Pending departures/arrivals includes tuples (endTime, trip)
        self.pending_departures = Queue.PriorityQueue()
        self.pending_arrivals = Queue.PriorityQueue()
        # Contains all resolved trips
        self.trip_list = []
        # List of trips that didn't end at the desired station due to a shortage
        self.bike_shortages = []
        self.dock_shortages = []
       

    def initialize(self, start_time):
        '''Sets states of stations at the start_time'''
        self.time = start_time
        # Stations should eventually be gotten from the database
        self.pending_departures = Queue.PriorityQueue()
        self.pending_arrivals = Queue.PriorityQueue()
        self.dock_shortages = []
        self.bike_shortages = []
        self.trip_list = []
        self.stations = {}
        self.initialize_stations(start_time)
        #for s in self.stations:
        #    print s, self.stations[s]

    def initialize_stations(self, start_time):
        '''Sets initial bike count for each station.'''
        queried_stations = self.session.query(data_model.Station)
        for s in queried_stations:
            # For now, generates a random count that is less than or equal to the station's capacity.
            count = random.randint(0,s.capacity)
            self.stations[s.id] = count
        

    def update(self, timestep):
        '''Moves the simulation forward one timestep from given time'''
        self.time += timestep
        self.generate_new_trips(self.time)
        self.resolve_trips()

        
    def generate_new_trips(self, timestep):
        '''Generates trips COMPLETELY RANDOMLY WOOO'''
            
        for station in self.stations:
            num_trips = random.randint(0,self.stations[station])
            for i in range(num_trips):
                end_station_ID = random.choice(self.stations.keys())
                start_time = self.time + datetime.timedelta(minutes=random.randint(0, timestep.total_seconds()/60))
                # Nobody takes longer than 2 hours to bike anywhere, duh!
                end_time = start_time + datetime.timedelta(minutes=random.randint(0, 120))
                new_trip = data_model.Trip(str(random.randint(1,500)), "Casual", "Produced", start_time, end_time, station, end_station_ID)

                self.pending_departures.put((start_time, new_trip))

                # print "GENERATED", printTrip(new_trip)

        # # TESTING
        # printedQueue = Queue.PriorityQueue()
        # print "PENDING TRIPS at time %s:" % str(self.time)
        # for i in range(self.pending_arrivals.qsize()):
        #     pq_trip = self.pending_arrivals.get()
        #     print pq_trip
        #     printedQueue.put(pq_trip)
        # self.pending_arrivals = printedQueue


    def resolve_trips(self):
        '''Resolves departures & arrivals within the current time interval'''
        # Get the first event, be it a departure or arrival.
        eventTuple = self.get_first_trip_event()
        eventType = eventTuple[0]
        trip = eventTuple[1]
        while eventType != None:
            if eventType == DEPARTURE_TYPE:
                if trip.start_date > self.time:
                    # Put trip back in proper queue if it's over the time, and stop the while loop
                    self.pending_departures.put((trip.start_date, trip))
                    break
                else:
                    # print "Resolving departure for \t", printTrip(trip)
                    self.resolve_departure(trip)
            elif eventType == ARRIVAL_TYPE:
                if trip.end_date > self.time:
                    self.pending_arrivals.put((trip.end_date, trip))
                    break
                else:
                    # print "Resolving arrival for \t\t", printToisson.ppf(.3,mu)rip(trip)
                    self.resolve_arrival(trip)
                    # print "If dock shortage, new trip is", printTrip(trip)

            eventTuple = self.get_first_trip_event()
            eventType = eventTuple[0]
            trip = eventTuple[1]
            
        # #TESTING
        # print "PENDING DEPARTURES at time %s:" % str(self.time)
        # printedQueue = Queue.PriorityQueue()
        # for i in range(self.pending_departures.qsize()):
        #     pq_trip = self.pending_departures.get()
        #     print printTrip(pq_trip[1])
        #     printedQueue.put(pq_trip)
        # self.pending_departures = printedQueue
        # print "PENDING ARRIVALS at time %s:" % str(self.time)
        # printedQueue = Queue.PriorityQueue()
        # for i in range(self.pending_arrivals.qsize()):
        #     pq_trip = self.pending_arrivals.get()
        #     print printTrip(pq_trip[1])
        #     printedQueue.put(pq_trip)
        # self.pending_arrivals = printedQueue
        # print "RESOLVED TRIPS at time %s:" % str(self.time)
        # for i in self.trip_list:
        #     print printTrip(i)


    def resolve_departure(self, trip):
        '''Decrement station count, put in pending_arrivals queue. If station is empty, put it in the bike_shortages list.'''
        departure_station_ID = trip.start_station_id
        if self.stations[departure_station_ID] == 0:
            self.bike_shortages.append(trip)
            self.resolve_sad_departure(trip)
        else:
            self.stations[departure_station_ID] -= 1
            self.pending_arrivals.put((trip.end_date, trip))

            
    def resolve_sad_departure(self, trip):
        '''When you want a bike but the station is empty'''
        pass

    def resolve_arrival(self, trip):
        '''Increment station count, put in trips list. If desired station is full, put it in the dock_shortages list and try again.'''
        arrival_station_ID = trip.end_station_id
        capacity = 5
        if self.stations[arrival_station_ID] == capacity:
            self.dock_shortages.append(trip)
            self.resolve_sad_arrival(trip)
        else:
            self.stations[arrival_station_ID] += 1
            self.trip_list.append(trip)


    def resolve_sad_arrival(self, trip):
        '''When you want to drop off a bike but the station is full'''
        # Randomly choose another station to try to park at, at a random time (< 2hrs) from now.
        trip.end_station_id = random.choice(self.stations.keys())
        trip.end_date += datetime.timedelta(minutes=random.randint(1, 120))
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


    def flush(self, to_database=False):
        '''Returns list of all trips since initialization, or adds them to the database if to_database is True'''
        if to_database:
            for trip in self.trip_list:
                self.session.add(trip)
            session.commit()
        else:
            return self.trip_list


    def cleanup(self):
        pass


# FOR TESTING
def printTrip(trip):
    return str(trip.start_station_id) + "-->" + str(trip.end_station_id) + ": " + str(trip.start_date) + " --> " + str(trip.end_date)


def main():
    SL = SimulationLogic()
    start_time = datetime.datetime(2013, 1, 1, 0, 0, 0)
    SL.initialize(start_time)
    step = datetime.timedelta(minutes=30)
    SL.update(step)
    SL.update(step)
    trips = SL.flush()
    # print "ALL TRIPS:"
    # for trip in trips:
    #     print printTrip(trip)
       

if __name__ == "__main__":
    main()
