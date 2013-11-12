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

class SummaryStatsHandler(RequestHandler):
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

application = Application([
    (r"/simulator", SummaryStatsHandler)
])

if __name__ == "__main__":
    application.listen(80)
    tornado.ioloop.IOLoop.instance().start()
