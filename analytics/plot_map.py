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
        return json.dumps(intersections_dict)

    def dump_json(self, to_dump):
        if self.indent:
            return json.dumps(to_dump, indent=4, default=self.json_dump_handler)
        else:
            return json.dumps(to_dump, default=self.json_dump_handler)

    def json_dump_handler(self, obj):
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        else:
            raise TypeError, 'Cannot serialize item %s of type %s' % (repr(obj), type(obj))

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
