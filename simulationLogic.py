'''
	TO DO:
	- Figure out how we get the timestep
	- How to keep priority queue sorted 
'''
# import data_model
import Queue
import random
import datetime

class SimulationLogic:
	def __init__(self, timestep):
		self.trip_list = []
		# Pending trips includes tuples (endTime, trip)
		self.pending_trips = Queue.PriorityQueue()
		# Assuming time and timestep will be in minutes from the start_time
		self.start_time = None
		self.time = None
		self.timestep = timestep
		# Connect to database through data_model?
		# {stID : count at self.time}
		self.stations = {0:10, 1:2, 2:14, 3:3, 4:8}
		# list of trips that didn't end at the desired station due to a dock shortage
		self.dock_shortages = []

	def initialize(self, start_time):
		'''Sets states of stations at the start_time'''
		self.time = 0
		self.start_time = start_time
		for station in self.stations:
			#Change this to a real thing from the database
			capacity = 20 
			self.stations[station] = random.randint(0, capacity)


	def update(self):
		'''Moves the simulation forward one timestep from given time'''
		self.generate_new_trips()
		self.time += self.timestep
		self.terminate_pending_trips()


	def generate_new_trips(self):
		'''Generates trips COMPLETELY RANDOMLY WOOO'''

		for station in self.stations:
			num_trips = random.randint(0,self.stations[station])
			for i in range(num_trips):
				end_station_ID = random.choice(self.stations.keys())
				start_time = self.time + random.randint(0, self.timestep)
				# Nobody takes longer than 2 hours to bike anywhere, duh!
				end_time = start_time + random.randint(0, 120)
				new_trip = [station, end_station_ID, start_time, end_time]

				self.pending_trips.put((new_trip[3], new_trip))

				self.stations[station] -= 1

		# TESTING
		print "PENDING TRIPS at time %d:" % (self.time)
		for trip in list(self.pending_trips.queue):
			print trip

		self.pending_trips.sort()

		# TESTING
		print "PENDING TRIPS at time %d:" % (self.time)
		for trip in list(self.pending_trips.queue):
			print trip


	def terminate_pending_trips(self):
		'''Adds any trips that have ended to self.trip_list, converting relative time to absolute time. Adds any trips that result in disappointment due to dock shortage to self.dock_shortages.'''
		# Go through data structure, if any trips end before current time, increment count on those stations & take trip out of structure
		trip = None
		if not self.pending_trips.empty():
			trip = self.pending_trips.get()[1]
		while trip != None and trip[3] < self.time:
			end_station_ID = trip[1]
			# Will get from database & end_station_ID
			capacity = 20
			if self.stations[trip[1]] == capacity:
				self.dock_shortages.append(trip)
				# Randomly choose another station to try to park at, at a random time (< 2hrs) from now.
				trip[1] = random.choice(self.stations.keys())
				trip[3] += random.randint(1, 120)
				self.pending_trips.put((trip[3], trip))
			else:
				self.stations[trip[1]] += 1
				self.trip_list.append([trip[0], trip[1], self.convertTime(trip[2]), self.convertTime(trip[3])])
			if not self.pending_trips.empty():
				trip = self.pending_trips.get()[1]
			else:
				trip = None

		# TESTING
		print "ALL TRIPS:"
		for trip in self.trip_list:
			print trip

		print "STILL PENDING TRIPS:"
		for trip in list(self.pending_trips.queue):
			print trip

	def flush(self):
		'''Returns list of all trips since initialization'''
		return self.trip_list


	def cleanup(self):
		pass


	def convertTime(self, minutes_from_start):
		'''Given minutes from start_time, returns a datetime object for the absolute time'''
		time_interval = datetime.timedelta(minutes=minutes_from_start)
		return self.start_time + time_interval