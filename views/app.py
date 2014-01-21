#!/usr/bin/env python

import tornado.ioloop
import datetime
import os


from analytics import PlotMap
from tornado.web import RequestHandler, Application
from analytics import SummaryStats


class StatsHandler(RequestHandler):
    def get(self):
        self.render("stats.html", title="Get Summary Stats on Generated Bike Trips")

    def post(self):
        start_date = datetime.datetime.strptime(self.get_argument("start"),
                                                "%m-%d-%Y %H:%M")
        end_date = datetime.datetime.strptime(self.get_argument("end"),
                                              "%m-%d-%Y %H:%M")
        
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
        intersections = PlotMap(day, start_time, end_time).intersections
        self.render("home.html", title="BikeShare Comps", locations=intersections)

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
        (r"/stats", StatsHandler)
    ], **settings)
    
    application.listen(3000)
    tornado.ioloop.IOLoop.instance().start()
