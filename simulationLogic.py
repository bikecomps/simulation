'''
    TO DO:
    - Use datetime.timedeltas for time and timestep
    - Test using Trip objects instead of tuples. (trip type = 'provided')
    - Figure out how we get the timestep
    - How to keep priority queue sorted
    - connect to database
'''
import data_model
import Queue
import random
import datetime

class SimulationLogic:
    def __init__(self):
        self.trip_list = []
        # Pending trips includes tuples (endTime, trip)
        self.pending_departures = Queue.PriorityQueue()
        self.pending_arrivals = Queue.PriorityQueue()
        # Assuming time and timestep will be in minutes from the start_time
        self.start_time = None
        self.time = None
        # Connect to database through data_model?
        # {stID : count at self.time}
        self.stations = {}
        # list of trips that didn't end at the desired station due to a dock shortage
        self.dock_shortages = []
        self.bike_shortages = []
        
    def initialize(self, start_time):
        '''Sets states of stations at the start_time'''
        self.time = 0
        self.start_time = start_time
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
                start_time = self.time + random.randint(0, timestep)
                # Nobody takes longer than 2 hours to bike anywhere, duh!
                end_time = start_time + random.randint(0, 120)
                # new_trip = [station, end_station_ID, start_time, end_time]
                new_trip =  data_model.Trip(str(random.randint(1,500)), "Casual", "Produced", start_time, end_time, station, end_station_ID)

                self.pending_departures.put((start_time, new_trip))

                print "GENERATED", new_trip

        # TESTING
        printedQueue = Queue.PriorityQueue()
        print "PENDING TRIPS at time %d:" % (self.time)
        for i in range(self.pending_arrivals.qsize()):
            pq_trip = self.pending_arrivals.get()
            print pq_trip
            printedQueue.put(pq_trip)
        self.pending_arrivals = printedQueue


    def resolve_departure(self, trip):
        '''Decrement station count, put in pending_arrivals queue. If station is empty, put it in the bike_shortages list.'''
        departure_station_ID = trip[0]
        if self.stations[departure_station_ID] == 0:
            self.bike_shortages.append(trip)
        else:
            self.stations[departure_station_ID] -= 1
            self.pending_arrivals.put((trip[3], trip))

            

    def resolve_arrival(self, trip):
        '''Increment station count, put in trips list. If desired station is full, put it in the dock_shortages list and try again.'''
        arrival_station_ID = trip[1]
        capacity = 5
        if self.stations[arrival_station_ID] == capacity:
            self.dock_shortages.append(trip)
            # Randomly choose another station to try to park at, at a random time (< 2hrs) from now.
            trip[1] = random.choice(self.stations.keys())
            trip[3] += random.randint(1, 120)
            self.pending_arrivals.put((trip[3], trip))
        else:
            self.stations[arrival_station_ID] += 1
            self.trip_list.append([trip[0], trip[1], self.convertTime(trip[2]), self.convertTime(trip[3])])


    def get_first_trip_event(self):
        '''Returns a tuple for the first departure or arrival's trip including (type of event, trip). Type of event is either 2 for departure, or 3 for arrival, or None. (This decision is due to which index the corresponding time is at in a trip.)'''
        if self.pending_departures.empty() and self.pending_arrivals.empty():
            trip = None
            eventType = None
        elif self.pending_arrivals.empty():
            trip = self.pending_departures.get()[1]
            eventType = 2
        elif self.pending_departures.empty():
            trip = self.pending_arrivals.get()[1]
            eventType = 3
        else:
            first_departure = self.pending_departures.get()[1]
            first_arrival = self.pending_arrivals.get()[1]
            # Departures have priority?
            print "Departure", first_departure[2], "Arrival", first_arrival[3]
            if (first_departure[2] <= first_arrival[3]):
                trip = first_departure
                eventType = 2
                self.pending_arrivals.put((first_arrival[3], first_arrival))
            else:
                trip = first_arrival
                eventType = 3
                self.pending_departures.put((first_departure[2], first_departure))
        return (eventType, trip)

    def resolve_trips(self):
        '''Resolves departures & arrivals within the current time interval'''
        # Get the first event, be it a departure or arrival.
        eventTuple = self.get_first_trip_event()
        eventType = eventTuple[0]
        trip = eventTuple[1]
        while eventType != None:
            if trip[eventType] >= self.time:
                # Put trip back in proper queue if it's over the time, and stop the while loop
                if eventType == 2:
                        self.pending_departures.put((trip[2], trip))
                elif eventType == 3:
                        self.pending_arrivals.put((trip[3], trip))
                break
            if eventType == 2:
                print "Resolving departure for", trip
                self.resolve_departure(trip)
            elif eventType == 3:
                print "Resolving arrival for", trip
                self.resolve_arrival(trip)
                print "If dock shortage, new trip is", trip

            eventTuple = self.get_first_trip_event()
            eventType = eventTuple[0]
            trip = eventTuple[1]
            
        #TESTING
        print "PENDING DEPARTURES at time %d:" % (self.time)
        printedQueue = Queue.PriorityQueue()
        for i in range(self.pending_departures.qsize()):
            pq_trip = self.pending_departures.get()
            print pq_trip
            printedQueue.put(pq_trip)
        self.pending_departures = printedQueue
        print "PENDING ARRIVALS at time %d:" % (self.time)
        printedQueue = Queue.PriorityQueue()
        for i in range(self.pending_arrivals.qsize()):
            pq_trip = self.pending_arrivals.get()
            print pq_trip
            printedQueue.put(pq_trip)
        self.pending_arrivals = printedQueue
        print "RESOLVED TRIPS:"
        for i in self.trip_list:
            print i


        # def terminate_pending_arrivals(self):
        #       '''Adds any trips that have ended to self.trip_list, converting relative time to absolute time. Adds any trips that result in disappointment due to dock shortage to self.dock_shortages.'''
        #       # Go through data structure, if any trips end before current time, increment count on those stations & take trip out of structure
        #       trip = None
        #       if not self.pending_arrivals.empty():
        #               trip = self.pending_arrivals.get()[1]
        #       while trip != None:
        #               if trip[3] > self.time:
        #                       self.pending_arrivals.put((trip[3], trip))
        #                       break
        #               end_station_ID = trip[1]
        #               # Will get from database & end_station_ID
        #               capacity = 5
        #               if self.stations[trip[1]] == capacity:
        #                       self.dock_shortages.append(trip)
        #                       # Randomly choose another station to try to park at, at a random time (< 2hrs) from now.
        #                       trip[1] = random.choice(self.stations.keys())
        #                       trip[3] += random.randint(1, 120)
        #                       self.pending_arrivals.put((trip[3], trip))
        #               else:
        #                       self.stations[trip[1]] += 1
        #                       self.trip_list.append([trip[0], trip[1], self.convertTime(trip[2]), self.convertTime(trip[3])])

        #               if not self.pending_arrivals.empty():
        #                       trip = self.pending_arrivals.get()[1]
        #               else:
        #                       trip = None

        #       # TESTING
        #       print "ALL TRIPS:"
        #       for trip in self.trip_list:
        #               print trip

        #       print "STILL PENDING TRIPS:"
        #       printedQueue = Queue.PriorityQueue()
        #       print "PENDING TRIPS at time %d:" % (self.time)
        #       for i in range(self.pending_arrivals.qsize()):
        #               pq_trip = self.pending_arrivals.get()
        #               print pq_trip
        #               printedQueue.put(pq_trip)
        #       self.pending_arrivals = printedQueue

    def flush(self):
        '''Returns list of all trips since initialization'''
        for trip in self.trip_list:
            print trip
        return self.trip_list


    def cleanup(self):
        pass


    def convertTime(self, minutes_from_start):
        '''Given minutes from start_time, returns a datetime object for the absolute time'''
        time_interval = datetime.timedelta(minutes=minutes_from_start)
        return self.start_time + time_interval
