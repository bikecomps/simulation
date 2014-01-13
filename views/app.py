#!/usr/bin/env python

import tornado.ioloop
from tornado.web import RequestHandler, Application

from logic import *
from utils import Connector

import datetime
import os

logic_options = {
    "SimulationLogic" : SimulationLogic,
    "PoissonLogic" : PoissonLogic
}

class StatsHandler(RequestHandler):
    def post(self):
        self.render("stats.html", title="See Raw Bike Trips generate")

    def get(self):
        try:
            logic_name = self.get_argument("logic", "PoissonLogic")
            start_date = datetime.datetime.strptime(self.get_argument("start"),
                                                    "%Y-%m-%d")
            end_date = datetime.datetime.strptime(self.get_argument("end"),
                                                  "%Y-%m-%d")
            session = Connector().getDBSession()
            logic = logic_options[logic_name](session)
            simulator = Simulator(logic)
            results = simulator.run(start_date, end_date)
            self.write(simulator.write_stdout(results['trips']).replace("\n", "<br/>\n"))
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
