#! /usr/bin/env python

from utils import Connector
from models import *

import csv
import datetime
import numpy
import sys
import json

class PlotMap:
    def __init__(self, day, start_hour, end_hour):
        
        self.day = day
        self.start_hour = start_hour
        self.end_hour = end_hour

        self.session = Connector().getDBSession()
        self.indent = False
        self.stations = self.get_stations()

    def get_stations(self):
        
        stations_dict = {}
        stations_counter = 0

	stations = self.session.query(Station)
	for station in stations:
		id = station.id
		name = station.name
		capacity = station.capacity
		intersection_id = station.intersection_id
		intersections= self.session.query(Intersection).filter(Intersection.id==intersection_id)
		for intersection in intersections:
			#print station.name
			#print intersection.lat
			#print intersection.lon
			stations_dict[stations_counter] = [intersection.lat, intersection.lon, id, name, capacity]
		stations_counter+=1
	return json.dumps(stations_dict)

def main():

# DEPRECATED. DO NOT RUN THIS FILE DIRECTLY.

    day = 1
    start_time = datetime.datetime.strptime('06:00',
                                            '%H:%M')
    end_time = datetime.datetime.strptime('20:00',
                                          '%H:%M')
                                          
    plotter = PlotMap(day, start_time, end_time)
    plotter.indent = True

    return plotter.intersection

if __name__ == '__main__':
    main()
