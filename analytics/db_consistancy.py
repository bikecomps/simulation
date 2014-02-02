from utils import *
from models import *
import numpy
import scipy.stats as stats

'''
So basically, the API sucks. Returning inconsistant counts
across statuses. So we're going to just use the mode for now.
Because what else to do?
'''

# Test and print stats on whether the capacities of the stations match 
# what's recorded in the station statuses we grab. 
def test_capacities(session):
    '''
    Reset the stations to have capacity equal to the mode of all observed counts
    '''
    stations = {s.id:s for s in session.query(Station)}
    consistant = 0
    inconsistant = 0

    statuses = list(session.query(StationStatus))

    station_counts = {s_id:[] for s_id in stations.iterkeys()}

    for ss in statuses:
        station_counts[ss.station_id].append(ss.bike_count + ss.empty_docks)

    unmatched = 0
    # Calculate the mode for each station, reassigning the capacity to the mode
    # if they're not the same
    for s_id, counts in station_counts.iteritems():
        count_d = {c:counts.count(c) for c in counts}
        mode = max(count_d, key=count_d.get)
        if stations[s_id].capacity != mode:
            unmatched += 1
            print "Station",s_id,"Cap",stations[s_id].capacity,"mode",mode
        stations[s_id].capacity = mode

    session.commit()
    print "Unmatched? ",unmatched


def gamma_test(durations):
    try:
        fit = stats.gamma.fit(durations, floc=0, fscale=1)
        chi, p = stats.kstest(durations, 'gamma', fit)
        return p
    except Exception:
        return None

def normal_test(durations):
    try:
        chi, p = stats.normaltest(durations)
        return p
    except Exception:
        return None

def test_trip_time_distribution(session, test, limit=1500):
    st_ids = list(session.query(Station.id).all())
    p_vals = []

    s_count = 0
    for s_id in st_ids:
        end_stations = {e_id[0]:[] for e_id in st_ids}
        for t in session.query(Trip).filter(Trip.start_station_id == s_id)\
                .yield_per(5000):
                end_stations[t.end_station_id].append(t.duration().total_seconds())
        for e_id, durations in end_stations.iteritems():
            if len(durations) > limit:
                 p = test(durations) 
                 if p:
                     p_vals.append(p)

        s_count += 1
        if s_count % 10 == 0:
            print "Done with ",s_count

    print "Avg.",sum(p_vals)/len(p_vals)
    s = sorted(p_vals)
    print "Quartiles", s[0], s[len(p_vals)/4], \
                    s[len(p_vals)/2], s[3*len(p_vals)/4], s[-1]


def main():
    s = Connector().getDBSession()
    #test_capacities(s)
    test_trip_time_distribution(s, normal_test)


if __name__ == '__main__':
    main()
