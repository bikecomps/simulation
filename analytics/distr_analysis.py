#! /usr/bin/env python

from models import *
from utils import Connector
import random
from collections import defaultdict
import math

import numpy as np
import scipy.stats as stats
from operator import itemgetter
import matplotlib
matplotlib.use('Agg')
import matplotlib.mlab as mlab
import matplotlib.pyplot as plt

allmeans = []
allstds = []

def get_data_for_station_pair(session, station_one, station_two, 
                              date_one="2010-01-01", date_two="2014-1-1",
                              count=100):
    values = session.query(Trip).filter(Trip.start_station_id==station_one) \
        .filter(Trip.end_station_id == station_two) \
        .filter(Trip.start_date.between(date_one, date_two))\
        .join(TripType, aliased=True)\
        .filter(TripType.trip_type != "Removed")\


    return values

def sample_distrs(conn, choice, samples=10, sam_size=100, 
                            date_one="2010-01-01", date_two="2014-01-01"):
    # Get a number of pairs
    q = """
        SELECT start_station_id, end_station_id
            FROM trips
            GROUP BY start_station_id, end_station_id
            HAVING COUNT(*) >= {count};
        """.format(count=sam_size)
    engine = conn.getDBEngine()
    session = conn.getDBSession()
    cand_stations = list(engine.execute(q))

    for i in xrange(samples):
        s_id, e_id = random.choice(cand_stations)
        trips = get_data_for_station_pair(session, s_id, e_id)
        choice(trips, s_id, e_id)



def num_departures_distributions(results):
    freqs = [0] * 24
    for trip in results:
        freqs[trip.start_date.hour] += 1
    x = np.array(freqs)

    mean = np.mean(x)
    var = np.var(x)
    allmeans.append(mean)
    allstds.append(var)
    print "mean=", mean
    print "var=", var

def num_arrivals_distributions(results):
    pass

def plot_dur_distributions(results, s_id, e_id):
    trip_lengths = [t.duration().total_seconds() for t in results]
    num_bins = 30


    # Still a ton of outliers! Remove top 20 values?
    trip_lengths = sorted(trip_lengths)#[:-20]

    mean = np.average(trip_lengths)
    std = np.std(trip_lengths)
    print "Avg.",np.average(trip_lengths),"Variance",math.sqrt(np.std(trip_lengths))
    n, bins, patches = plt.hist(trip_lengths, num_bins, 
                                facecolor='blue', normed=True, alpha=.7)#, log=True)
    y = mlab.normpdf(bins, mean, std)
    plt.plot(bins, y, 'r--', linewidth=3, label='Normal Distr.')
    plt.xlabel('Average Trip Duration (s)')
    plt.ylabel('Observed Occurrences (normalized)')
    plt.title('Trips Between Station %s and %s' % (s_id, e_id))
    plt.legend()
    #filename = "analytics/distr_output/gamma_normal_distrs/trip_durs-{s_id}-{e_id}-{type}.png"
    filename = "trip_durs-{s_id}-{e_id}-{type}.png"
    plt.savefig(filename.format(s_id=s_id, e_id=e_id, type='normal'))

    shape, loc, scale = stats.gamma.fit(trip_lengths, floc=0, fscale=1)
    y = stats.gamma.pdf(bins, shape, scale=scale)
    plt.plot(bins, y, 'g--', linewidth=3, label='Gamma Distr.')
    plt.legend()
    plt.savefig(filename.format(s_id=s_id, e_id=e_id, type='gamma'))
    plt.clf()

def plot_poisson_hour(results, s_id, e_id):
    times = [[defaultdict(int)] * 24 for x in range(7)]
    for t in results:
        t_time = t.start_date
        times[t_time.weekday()][t_time.hour][t.end_date.strftime("%Y-%m-%d")] += 1

    
    # Not great but look at the maximum number days with observations
    num_obs = [(d,h,len(times[d][h].values())) for d in range(7) for h in range(24)]
    day, hour, _ = max(num_obs, key=itemgetter(2))

    day_obs = [c for c in times[day][hour].itervalues()] 
    filename = "analytics/distr_output/poisson/Poiss-{s_id}-{e_id}-{h}-{d}.png"\
                    .format(s_id=s_id, e_id=e_id, h=hour, d=day)


    num_bins = 20
    n, bins, patches = plt.hist(day_obs, num_bins, facecolor='blue')
    plt.xlabel('Trip Times: %s -> %s' % (s_id, e_id))
    plt.ylabel('Counts')
    plt.title('Trip time destinations')
    plt.savefig(filename)
    plt.clf()


def gamma_test(durations):
    try:
        fit = stats.gamma.fit(durations, floc=0, fscale=1)
        chi, p = stats.kstest(durations, 'gamma', fit)
        return p
    except Exception, e:
        return None

def normal_test(durations):
    try:
        chi, p = stats.normaltest(durations)
        return p
    except Exception:
        return None

def test_trip_time_distribution(session, test, limit=100,
                                s_time="2010-01-01", e_time="2014-01-01"):
    st_ids = list(session.query(Station.id).all())
    p_vals = []

    s_count = 0
    for s_id in st_ids:
        end_stations = {e_id[0]:[] for e_id in st_ids}
        for t in session.query(Trip).filter(Trip.start_station_id == s_id)\
                .filter(Trip.start_date.between(s_time, e_time))\
                .join(TripType, aliased=True)\
                .filter(TripType.trip_type != "Removed")\
                .yield_per(5000):
                end_stations[t.end_station_id].append(t.duration().total_seconds())
        for e_id, durations in end_stations.iteritems():
            if len(durations) > limit:
                 p = test(durations) 
                 if p != None:
                     p_vals.append(p)

        s_count += 1
        if s_count % 10 == 0:
            print "Done with ",s_count

    print "Avg.",sum(p_vals)/len(p_vals)
    s = sorted(p_vals)
    print "Quartiles", s[0], s[len(p_vals)/4], \
                    s[len(p_vals)/2], s[3*len(p_vals)/4], s[-1]

def main():
    #random.seed()
    c = Connector()
    #trips = sample_distrs(c, plot_dur_distributions, samples=100)
    session = c.getDBSession()
    trips = get_data_for_station_pair(session, 31227, 31239)
    plot_dur_distributions(trips, 31227, 31239)

    return
    #sample_distrs(c, plot_dur_distributions, sam_size=300, samples=30,
    #              date_one="2013-01-01")
    #test_trip_time_distribution(c.getDBSession(), normal_test, limit=100)
    session = c.getDBSession()
    
    stations = session.query(Station).all()
    for s1 in stations:
        for s2 in stations:
            print "obtaining mean and std for s1=", s1.id, ";s2=", s2.id
            trips = get_data_for_station_pair(session, s1.id, s2.id, "2012-1-1", "2013-1-1").all()
            num_departures_distributions(trips)
    # trips = get_data_for_station_pair(session, 31248, 31206, "2012-1-1", "2013-1-1").all()
    # plot_time_distributions(trips)
    print "mean of means:", np.mean(np.array(allmeans))        
    print "mean of stds:", np.mean(np.array(allstds))
    # plot_num_arrivals_distributions(trips)

if __name__ == '__main__':
    main()
