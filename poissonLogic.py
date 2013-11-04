'''
    poissonLogic.py

    Questions we still have about distributions:
    - Do we have to specify standard deviation and whatever the poisson equivalent is? (Perhaps we use scipy's rvs function but I haven't figured it out yet.)
'''

from scipy.stats import poisson
from scipy.stats import norm

class PoissonLogic(SimulationLogic):

    def generate_new_trips(self, start_time):
        # Note that Monday is day 0 and Sunday is day 6. Is this the same for data_model?
        lambda_hour = start_time.hour
        lambda_day_of_week = start_time.weekday()
        lambda_start_time = start_time.replace(hour=lambda_hour)

        for start_station_id in self.stations:
            for end_station_id in self.stations:
                num_trips = self.get_num_trips()
                for i in range(num_trips):
                    # Starting time of the trip is randomly chosen within the Lambda's time range, which is hard-coded to be an hour.
                    added_time = datetime.timedelta(0, random.randint(0, 59), 0, 0, random.randint(0, 59), 0, 0)
                    trip_start_time = lambda_start_time + added_time
                    trip_duration = self.get_trip_duration()
                    new_trip = data_model.Trip(str(random.randint(1,500)), "Casual", "Produced", trip_start_time, trip_end_time, start_station_id, end_station_id)
                    self.pending_departures.put((start_time, new_trip))

                


    def get_num_trips(self, start_station_id, end_station_id, hour, day_of_week):
        '''Return the number of trips between 2 stations at a given time, sampled from poisson distribution'''
        # Get the proper lambda from the database
        lambda_poisson = self.session.query(data_model.Lambda)\
                                .filter(data_model.Lambda.start_station_id = start_station_id)\
                                .filter(data_model.Lambda.end_station_id = end_station_id)\
                                .filter(data_model.Lambda.hour = lambda_hour)\
                                .filter(data_model.Lambda.day_of_week = lambda_day_of_week)
        # Choose a random probability. We will get the number of trips that happen with that probability using the inverse cumulative distribution for poisson.
        probability = random.random()
        while probability == 0:
            probability = random.random()
        num_trips = poisson.ppf(probability,lambda_poisson)
        return num_trips

    def get_trip_duration(self, start_station_id, end_station_id, ):
        '''Get timedelta of a trip between 2 stations, sampled from normal distribution'''
        # Get the proper mu from the database
        # mu_normal = self.session.query(data_model.Mu)\
                        # .filter(???)
        mu_normal = 5
        probability = random.random()
        while probability == 0:
            probability = random.random()
        num_trips = poisson.ppf(probability,lambda_poisson)
        return datetime.timedelta(minutes=norm.ppf(probability,mu_normal))

    def resolve_departure(self, trip):
        pass