'''
    poissonLogic.py

    Questions we still have about distributions:
    - Do we have to specify standard deviation and whatever the poisson equivalent is? (Perhaps we use scipy's rvs function but I haven't figured it out yet.)
'''
from utility import Connector
import data_model
from scipy.stats import poisson
import numpy
import random
from simulationLogic import SimulationLogic
import datetime

class PoissonLogic(SimulationLogic):

    def __init__(self, session):
        SimulationLogic.__init__(self, session)

    def generate_new_trips(self, start_time):
        # Note that Monday is day 0 and Sunday is day 6. Is this the same for data_model?
        lambda_hour = start_time.hour
        lambda_day_of_week = start_time.weekday()
        lambda_start_time = start_time.replace(hour=lambda_hour)

        station_count = 0
        # Cache off distributions to increase speed for actual simulation
        gaussian_distrs = self.get_gaussians()
        lambda_distrs = self.get_lambdas(lambda_hour, lambda_day_of_week)

        for start_station_id in self.stations:
            station_count += 1
            for end_station_id in self.stations:
                lam = lambda_distrs.get((start_station_id, end_station_id), -1)
                gauss = gaussian_distrs.get((start_station_id, end_station_id), -1)
                num_trips = self.get_num_trips(lam)

                if gauss >= 0:
                    for i in range(num_trips):
                        # Starting time of the trip is randomly chosen within the Lambda's time range, which is hard-coded to be an hour.
                        added_time = datetime.timedelta(0, random.randint(0, 59), 0, 0, random.randint(0, 59), 0, 0)
                        trip_start_time = lambda_start_time + added_time
                        trip_duration = self.get_trip_duration(gauss)
                        trip_end_time = trip_start_time + trip_duration
                        new_trip = data_model.Trip(str(random.randint(1,500)), "Casual", "Produced", \
                                trip_start_time, trip_end_time, start_station_id, end_station_id)
                        self.pending_departures.put((start_time, new_trip))

                

    def get_num_trips(self, lam):
        probability = random.random()
        while probability == 0:
            probability = random.random()
        num_trips = poisson.ppf(probability, lam.value)
        if numpy.isnan(num_trips):
            #TODO: Should we do something here?
            num_trips = -1
        #print "Num trips: ", num_trips
        return int(num_trips)


    def get_gaussians(self):
        gaussian_distr = self.session.query(data_model.GaussianDistr)

        distr_dict = {}
        for gauss in gaussian_distr:
            distr_dict[(gauss.start_station_id, gauss.end_station_id)] = gauss
        return distr_dict

    def get_lambdas(self, hour, day_of_week):
        lambda_poisson = self.session.query(data_model.Lambda)\
                .filter(data_model.Lambda.hour == hour)\
                .filter(data_model.Lambda.day_of_week == day_of_week)
        # (station_id_1,  station_id_2) -> lambda
        distr_dict = {}

        for lam in lambda_poisson:
            distr_dict[(lam.start_station_id, lam.end_station_id)] = lam

        return distr_dict


    def get_trip_duration(self, gauss):
        trip_length = random.gauss(gauss.mean, gauss.std)
        return datetime.timedelta(seconds=trip_length)

    def resolve_sad_arrival(self, trip):
        '''
        Changes trip.end_station_id to the id of the station nearest to it and updates trip.end_date accordingly. Puts the updated trip into pending_arrivals.
        '''
        arrive_station_id = trip.end_station_id
        # SELECT station2_id from station_distances WHERE station1_id=arrive_station_id order by distance limit 1;
        # returns a StationDistance object in which station2_id is the station nearest to arrive_station_id
        nearest_distance = self.session.query(data_model.StationDistance)\
                                    .filter(data_model.StationDistance.station1_id == arrive_station_id)\
                                    .order_by(data_model.StationDistance.distance)[0]
        nearest_station_id = nearest_distance.station2_id
        trip.end_station_id = nearest_station_id
        extra_time = self.get_trip_duration(arrive_station_id, nearest_station_id)
        trip.end_date = trip.end_date + extra_time
        self.pending_arrivals.put(trip.end_date,trip)



    def resolve_sad_departure(self, trip):
        '''
        Currently changes trip.start_station_id to the id of the station nearest to it. Updates both trip.start_date and trip.end_date using get_trip_duration(), puts the updated trip into pending_departures. 
        '''
        depart_station_id = trip.start_station_id
        # SELECT station2_id from station_distances WHERE station1_id=depart_station_id order by distance limit 1;
        # returns a StationDistance object in which station2_id is the station nearest to arrive_station
        nearest_distance = self.session.query(data_model.StationDistance)\
                                    .filter(data_model.StationDistance.station1_id == depart_station_id)\
                                    .order_by(data_model.StationDistance.distance)[0]
        nearest_station_id = nearest_distance.station2_id
        trip.start_station_id = nearest_station_id
        # Calculation for extra_time assumes that the user spends as much time walking to the nearest station as they would biking, which might be a bad assumption
        extra_time = self.get_trip_duration(depart_station_id, nearest_station_id)
        # Should trip.start_date not change? Should we include a way to note that this trip started out as a failure?
        trip.start_date = trip.start_date + extra_time
        new_trip_duration = self.get_trip_duration(nearest_station_id,trip.end_station_id)
        trip.end_date = trip.start_date + trip.end_date
        self.pending_departures.put(trip.start_date, trip)

    def clean_up(self):
        pass

def main():
    connector = Connector()
    session = connector.getDBSession()
    p = PoissonLogic(session)
    print p.get_trip_duration(31100, 31101)

if __name__ == '__main__':
    main()
