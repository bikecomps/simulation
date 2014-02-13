#!/usr/bin/env python

import tornado.ioloop
import datetime
import os


from analytics import PlotMap
from tornado.web import RequestHandler, Application
from analytics import SummaryStats

class UnifiedHandler(RequestHandler):
    def get(self):
        
        stations = PlotMap(None, None, None).stations
        self.render("unified.html",title="Simba | Simulation of Bike Availability",locations=stations)
    
    def post(self):
        start_date = datetime.datetime.strptime(self.get_argument("start"),
                                                "%Y-%m-%d %H:%M")
        end_date = datetime.datetime.strptime(self.get_argument("end"),
                                              "%Y-%m-%d %H:%M")
 
        sstats = SummaryStats(start_date, end_date)
        self.write(sstats.get_stats())        
         

class StatsHandler(RequestHandler):
    def get(self):
        self.render("stats.html", title="Get Summary Stats on Generated Bike Trips")

    def post(self):
        start_date = datetime.datetime.strptime(self.get_argument("start"),
                                                "%Y-%m-%d %H:%M")
        end_date = datetime.datetime.strptime(self.get_argument("end"),
                                              "%Y-%m-%d %H:%M")
        
        sstats = SummaryStats(start_date, end_date)
        self.write(sstats.get_stats())        
    
class IndexHandler(RequestHandler):
    def get(self):
        '''
        Dummy data for Google Maps. Queries Monday 6am-8pm for testing purposes.
        '''
        day = 1
        start_time = datetime.datetime.strptime('06:00',
                                            '%H:%M')
        end_time = datetime.datetime.strptime('20:00',
                                          '%H:%M')
        stations = PlotMap(day, start_time, end_time).stations
        self.render("home.html", title="BikeShare Comps", locations=stations)

class AboutHandler(RequestHandler):
    def get(self):
        self.render("about.html", title="About Us")

class BaseHandler(RequestHandler):
    def get(self):
        self.render("base.html", title="Base File")

if __name__ == "__main__":
    dirname = os.path.dirname(__file__)
    settings = {
        "static_path" : os.path.join(dirname, "static"),
        "template_path" : os.path.join(dirname, "templates")
    }
    application = Application([
        (r"/", IndexHandler),
        (r"/base", BaseHandler),
        (r"/about", AboutHandler),
        (r"/stats", StatsHandler),
	(r"/unified", UnifiedHandler)
    ], **settings)
    application.listen(1337)
    tornado.ioloop.IOLoop.instance().start()
