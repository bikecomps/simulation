'''
    poissonLogic.py
'''

from scipy.stats import poisson
from scipy.stats import norm

class PoissonLogic(SimulationLogic):

    def generate_new_trips(self, start_time):
        for start_station_id in self.stations:
            for end_station_id in self.stations:
                # Get a lambda from the database
                # self.session.query(data_model.Lambda).filter(data_model.Lambda.start_station = start_station_id).filter(data_model.Lambda.end_station = end_station_id)
                mu = 5 # LOL
                q = random.random()
                # don't want to include 0 -- is there a better way to do this?
                while q == 0:
                    q = random.random()
                num_trips = poisson.ppf(q,mu)
                for i in range(num_trips):

                    new_trip = data_model.Trip(str(random.randint(1,500)), "Casual", "Produced", start_time, end_time, start_station_id, end_station_id)
                    self.pending_departures.put((start_time, new_trip))

                


                # for i in range(num_trips):
       #              end_station_ID = random.choice(self.stations.keys())
       #              start_time = self.time + datetime.timedelta(minutes=random.randint(0, timestep.total_seconds()/60))
       #              # Nobody takes longer than 2 hours to bike anywhere, duh!
       #              end_time = start_time + datetime.timedelta(minutes=random.randint(0, 120))
       #              new_trip = data_model.Trip(str(random.randint(1,500)), "Casual", "Produced", start_time, end_time, station, end_station_ID)

       #              self.pending_departures.put((start_time, new_trip))

    def resolve_departure(self, trip):
