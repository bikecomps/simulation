'''
    TO DO:
    - connect to database
'''
# import data_model
import Queue
import random
import datetime
# # Might need to move this to simulator eventually
# import hidden
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker
DEPARTURE_TYPE = 0
ARRIVAL_TYPE = 1

class SimulationLogic:

    def __init__(self):
        self.trip_list = []
        # Pending departures/arrivals includes tuples (endTime, trip)
        self.pending_departures = Queue.PriorityQueue()
        self.pending_arrivals = Queue.PriorityQueue()
        # self.time is in datetime format, represents the current time in the simulator.
        self.time = None
        # Connect to database through data_model?
        # {stID : count at self.time}
        self.stations = {}
        # list of trips that didn't end at the desired station due to a dock shortage
        self.dock_shortages = []
        self.bike_shortages = []

        # Might need to move all this to simulator eventually
        # engine_path = 'postgresql://%s:%s@localhost/%s' % (hidden.DB_USERNAME, hidden.DB_PASSWORD, hidden.DB_NAME)

        # # echo=False is unnecessary but setting it to True provides useful info.
        # engine = create_engine(engine_path, echo=False)
        # Session = sessionmaker(bind=engine)
        # self.session = Session()
                
    def initialize(self, start_time):
        '''Sets states of stations at the start_time'''
        self.time = start_time
        self.stations = {0:5, 1:5, 2:5, 3:5, 4:4}
        self.pending_departures = Queue.PriorityQueue()
        self.pending_arrivals = Queue.PriorityQueue()
        # for station in self.stations:
        #Change this to a real thing from the database
        # capacity = 20 
        # self.stations[station] = random.randint(0, capacity)
        

    def update(self, timestep):
        '''Moves the simulation forward one timestep from given time'''
        self.generate_new_trips(timestep)
        self.time += timestep
        self.resolve_trips()
        # self.terminate_pending_arrivals()

        
    def generate_new_trips(self, timestep):
        '''Generates trips COMPLETELY RANDOMLY WOOO'''
            
        for station in self.stations:
            num_trips = random.randint(0,self.stations[station])
            print "STATION", station, "HAS", self.stations[station], "BIKES"
            for i in range(num_trips):
                end_station_ID = random.choice(self.stations.keys())
                start_time = self.time + datetime.timedelta(minutes=random.randint(0, timestep.total_seconds()/60))
                # Nobody takes longer than 2 hours to bike anywhere, duh!
                end_time = start_time + datetime.timedelta(minutes=random.randint(0, 120))
                # new_trip = [station, end_station_ID, start_time, end_time]
                new_trip =  Trip(str(random.randint(1,500)), "Casual", "Produced", start_time, end_time, station, end_station_ID)

                self.pending_departures.put((start_time, new_trip))

                print "GENERATED", new_trip

        # TESTING
        printedQueue = Queue.PriorityQueue()
        print "PENDING TRIPS at time %s:" % str(self.time)
        for i in range(self.pending_arrivals.qsize()):
            pq_trip = self.pending_arrivals.get()
            print pq_trip
            printedQueue.put(pq_trip)
        self.pending_arrivals = printedQueue


    def resolve_departure(self, trip):
        '''Decrement station count, put in pending_arrivals queue. If station is empty, put it in the bike_shortages list.'''
        departure_station_ID = trip.start_station_id
        if self.stations[departure_station_ID] == 0:
            self.bike_shortages.append(trip)
        else:
            self.stations[departure_station_ID] -= 1
            self.pending_arrivals.put((trip.end_date, trip))

            

    def resolve_arrival(self, trip):
        '''Increment station count, put in trips list. If desired station is full, put it in the dock_shortages list and try again.'''
        arrival_station_ID = trip.end_station_id
        capacity = 5
        if self.stations[arrival_station_ID] == capacity:
            self.dock_shortages.append(trip)
            # Randomly choose another station to try to park at, at a random time (< 2hrs) from now.
            trip.end_station_id = random.choice(self.stations.keys())
            trip.end_date += datetime.timedelta(minutes=random.randint(1, 120))
            self.pending_arrivals.put((trip.end_date, trip))
        else:
            self.stations[arrival_station_ID] += 1
            self.trip_list.append(trip)


    def get_first_trip_event(self):
        '''Returns a tuple for the first departure or arrival's trip including (type of event, trip). Type of event is either 2 for departure, or 3 for arrival, or None. (This decision is due to which index the corresponding time is at in a trip.)'''
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
            # Departures have priority?
            print "Departure", first_departure.start_date, "Arrival", first_arrival.end_date
            if (first_departure.start_date <= first_arrival.end_date):
                trip = first_departure
                eventType = DEPARTURE_TYPE
                self.pending_arrivals.put((first_arrival.end_date, first_arrival))
            else:
                trip = first_arrival
                eventType = ARRIVAL_TYPE
                self.pending_departures.put((first_departure.start_date, first_departure))
        return (eventType, trip)

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
                    print "Resolving departure for", trip
                    self.resolve_departure(trip)
            elif eventType == ARRIVAL_TYPE:
                if trip.end_date > self.time:
                    self.pending_arrivals.put((trip.end_date, trip))
                    break
                else:
                    print "Resolving arrival for", trip
                    self.resolve_arrival(trip)
                    print "If dock shortage, new trip is", trip

            eventTuple = self.get_first_trip_event()
            eventType = eventTuple[0]
            trip = eventTuple[1]
            
        #TESTING
        print "PENDING DEPARTURES at time %s:" % str(self.time)
        printedQueue = Queue.PriorityQueue()
        for i in range(self.pending_departures.qsize()):
            pq_trip = self.pending_departures.get()
            print pq_trip[1]
            printedQueue.put(pq_trip)
        self.pending_departures = printedQueue
        print "PENDING ARRIVALS at time %s:" % str(self.time)
        printedQueue = Queue.PriorityQueue()
        for i in range(self.pending_arrivals.qsize()):
            pq_trip = self.pending_arrivals.get()
            print pq_trip[1]
            printedQueue.put(pq_trip)
        self.pending_arrivals = printedQueue
        print "RESOLVED TRIPS:"
        for i in self.trip_list:
            print i

    def flush(self):
        '''Returns list of all trips since initialization'''
        for trip in self.trip_list:
            print trip
        return self.trip_list


    def cleanup(self):
        pass

class Trip():
    '''
    Stores all trips from test data as well as created trip data
    '''
    def __init__(self, bike_id, member_type, trip_type, start_date, end_date,
                 start_station_id, end_station_id):
        self.bike_id = bike_id
        self.member_type = member_type
        self.trip_type = trip_type
        self.start_date = start_date
        self.end_date = end_date
        self.start_station_id = start_station_id
        self.end_station_id = end_station_id

    def __str__(self):
        return str(self.start_station_id) + " -> " + str(self.end_station_id) + ": " + str(self.start_date) + ", " + str(self.end_date)


def main():
    SL = SimulationLogic()
    start_time = datetime.datetime(2013, 1, 1, 0, 0, 0)
    SL.initialize(start_time)
    step = datetime.timedelta(minutes=30)
    SL.update(step)
    SL.update(step)
    SL.flush()

if __name__ == "__main__":
    main()