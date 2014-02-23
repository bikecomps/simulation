#!/usr/bin/env python

import tornado.ioloop
from tornado.web import RequestHandler, Application

import pickle
import datetime

class PollingHandler(RequestHandler):
    """
    We run a polling server on port 3001. 
    This is used to report the progress of the simulation on every timestep.
    It returns 'current_time' and 'percent_progress' back to the front-end.

    Note: Because of CORS (Cross-Origin-Resource-Sharing) implementation,
    we have to allow communication via only one port. So for now,
    we do all communication via port 3000.
    """

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "http://cmc307-04.mathcs.carleton.edu:3000")

    def get(self):
        pb = pickle.load(open("progress_buffer.dat")) 

        info = {}               
        info["current_time"] = datetime.datetime.strftime(
            pb["current_time"], '%Y-%m-%d %H:%M'
        )
        if pb["total_steps"] > 0:
            info["percent_progress"] = float(pb["done_steps"])/pb["total_steps"] * 100
        else:
            info["percent_progress"] = 100

        self.write(info);

if __name__ == "__main__":
    application = Application([(r"/", PollingHandler)])

    port_num = 3001
    application.listen(port_num)
    print "listening on port", port_num

    tornado.ioloop.IOLoop.instance().start()
