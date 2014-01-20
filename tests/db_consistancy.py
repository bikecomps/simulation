from utils import *
from models import *
import numpy

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

def main():
    s = Connector().getDBSession()
    test_capacities(s)


if __name__ == '__main__':
    main()
