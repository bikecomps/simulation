#!/usr/bin/env python

import tornado.ioloop
import datetime
import os
import subprocess


from analytics import PlotMap
from tornado.web import RequestHandler, Application, asynchronous
from analytics import SummaryStats
from analytics import clustering

class UnifiedHandler(RequestHandler):

    def get(self):        
        stations = PlotMap().stations
        self.render("unified.html",title="Simba | Washington DC",locations=stations)

    def post(self):
        start_date = datetime.datetime.strptime(self.get_argument("start"), "%Y-%m-%d %H:%M")
        end_date = datetime.datetime.strptime(self.get_argument("end"), "%Y-%m-%d %H:%M")

        try:
            sstats = SummaryStats(start_date, end_date)
            self.write(sstats.get_stats())
        except Exception as e:
            print e
            # some error occurred
            self.write("{}")


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

class ClusterHandler(RequestHandler):
    def get(self):
        stations = PlotMap().stations
        self.render("clustering.html", title="Clustering Tool", locations=stations)

    def post(self):
        cluster_type = self.get_argument("clustering_method")
        clusters = clustering.get_clusters(cluster_type)        
        self.write(clusters)


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
        (r"/", UnifiedHandler),
        (r"/base", BaseHandler),
        (r"/about", AboutHandler),
        (r"/stats", StatsHandler),
        (r"/unified", UnifiedHandler),
        (r"/clustering", ClusterHandler)
    ], **settings)

    port_num = 1337
    application.listen(port_num)
    print "listening on port", port_num

    # run another server to use for long-polling
    cmd = ["python",
           "-m",
           "views.long_polling"]
    proc = subprocess.Popen(cmd)

    tornado.ioloop.IOLoop.instance().start()
