import tornado.ioloop
from tornado.web import RequestHandler, Application

from simulationLogic import SimulationLogic
from poissonLogic import PoissonLogic
from utility import Connector
from simulator import Simulator 

import datetime

logic_options = {
    "SimulationLogic" : SimulationLogic,
    "PoissonLogic" : PoissonLogic
}

class RawTripsHandler(RequestHandler):
    """
    To generate trips from Jan. 1, 2012 to Jan. 2, 2013 using
    the PoissonLogic simulator, use:

    http://localhost/raw?logic=PoissonLogic&start=2012-1-1&end=2013-1-1

    The default logic simulator is 'SimulationLogic'
    """
    def get(self):
        try:
            logic_name = self.get_argument("logic", "SimulationLogic")
            start_date = datetime.datetime.strptime(self.get_argument("start"),
                                                    "%Y-%m-%d")
            end_date = datetime.datetime.strptime(self.get_argument("end"),
                                                  "%Y-%m-%d")
            session = Connector().getDBSession()
            logic = logic_options[logic_name](session)
            simulator = Simulator(logic)
            results = simulator.run(start_date, end_date)
            self.write(simulator.write_stdout(results))
        except:
            self.write("An error occured!<br/>")
            self.write("Simulator usage: /simulator?logic=<some logic>&start=<start date>&end=<end date>")

class IndexHandler(RequestHandler):
    def get(self):
        self.render("index.html")

if __name__ == "__main__":
    dirname = os.path.dirname(__file__)
    settings = {
        "static_path" : os.path.join(dirname, "static"),
        "template_path" : os.path.join(dirname, "template")
    }
    application = Application([
        (r"/", IndexHandler),
        (r"/raw", RawTripsHandler)
    ], **settings)
    
    application.listen(80)
    tornado.ioloop.IOLoop.instance().start()
