#! /usr/bin/env python

from utils import Connector
from models import *

import csv
import datetime
import numpy
import sys

class PlotMap:
    def __init__(self, day, start_hour, end_hour):
        
        self.day = day
        self.start_hour = start_hour
        self.end_hour = end_hour

        self.session = Connector().getDBSession()

        self.intersections = self.get_coordinates()

    def get_coordinates(self):
        
        intersections_dict = {}
        intersections_counter = 0

        intersections = self.session.query(Intersection)
        for intersection in intersections:
            lat = intersection.lat
            lon = intersection.lon
            intersections_dict[intersections_counter] = [lat, lon]
            intersections_counter+=1

        return intersections_dict

def main():

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
