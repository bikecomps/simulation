#!/usr/bin/python
'''
A class for comparing the trips our simulator generates to real trips.
'''

from utils import Connector

class Evaluator:
	def __init__(self):
		self.trips = self.getTrips()
		self.stationPairs = self.setupStationPairs(self.trips)
	
	def compareTripNumbers(self,stationPair):
		numRealTrips = len(stationPair.realTrips)
		numGendTrips = len(stationPair.gendTrips)
		return numRealTrips - numGendTrips
		
	def compareAvgTripTimes(self,stationPair):
		totalRealTripTime = 0
		totalGendTripTime = 0
		for trip in stationPair.realTrips:
			tripLength = 1 # how should this be calculated?
			totalRealTripTime += tripLength
		for trip in stationPair.gendTrips:
			tripLength = 1 # how should this be calculated?
			totalGendTripTime += tripLength
		avgRealTripTime = totalRealTripTime / len(stationPair.realTrips)
		avgGendTripTime = totalGendTripTime / len(stationPair.gendTrips)
		return avgRealTripTime - avgGendTripTime
		
	def setupStationPairs(self,trips):
		stationPairs = {}
		for trip in trips:
			start = trip.getStart() # How do we work with trip objects?
			end = trip.getEnd()
			# if (start,end) not in stationPairs:
				# newStationPair = StationPair(start,end)
				# newStationPair.addTrip(trip)
				# stationPairs[(start,end)] = newStationPair
			# else:
				# stationPairs[(start,end)] = stationPairs[(start,end)].addTrip(trip)
		return stationPairs
	
	def getTrips(self):
		trips = []
		c = Connector()
		session = c.getDBSession()
    	engine = c.getDBEngine()
    	for trip in session.query(Trip) \
            .filter(Trip.type == 'production') \
            .yield_per(cap):
            # if there's a corresponding 'testing' trip in the databse:
            # 	trips.append(trip)
            # 	trips.append(the corresponding 'testing' trip)
        return trips
        
class StationPair:
	def __init__(self,start,end):
		self.startStation = start
		self.endStation = end
		self.realTrips = []
		self.gendTrips = []
	
	def addTrip(self,trip):
		if trip.isReal(): # ???
			self.realTrips.append(trip)
		elif trip.isGend(): # ???
			self.gendTrips.append(trip)
		else:
			print "Error: StationPair trips must be of type 'training' or 'product'."
			
def main():
	evaluator = Evaluator()
	for stationPair in evaluator.stationPairs:
		tripNumDiff = evaluator.compareTripNumbers(stationPair)
		print 'StationPair', stationPair, 'generated', tripNumDiff, 'fewer trips than reality.'

if __name__ == '__main__':
	main()
