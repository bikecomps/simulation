#!/usr/bin/env python

import tornado.ioloop
from tornado.web import RequestHandler, Application

from analytics import SummaryStats

import datetime
import os


class StatsHandler(RequestHandler):
    def get(self):
        self.render("stats.html", title="Get Summary Stats on Generated Bike Trips")

    def post(self):
        try:
            start_date = datetime.datetime.strptime(self.get_argument("start"),
                                                    "%m-%d-%Y %H:%M")
            end_date = datetime.datetime.strptime(self.get_argument("end"),
                                                  "%m-%d-%Y %H:%M")

            sstats = SummaryStats(start_date, end_date)

            self.write(sstats.get_stats())

        except Exception as inst:
            print "usage: /raw?logic=PoissonLogic&start=<start-date>&end=<end-date>"
            print inst
    
class IndexHandler(RequestHandler):
    def get(self):
        self.render("home.html", title="BikeShare Comps")

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
