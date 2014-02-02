import numpy as np
from utils import *
from models import *
from collections import defaultdict

def calc_outliers(session, s_id):
    # end_id -> trips
    trip_times = defaultdict(list)

    for t in session.query(Trip).filter(Trip.start_station_id == s_id)\
                .join(TripType, aliased=True)\
                .filter(TripType.trip_type != "Produced").all():
        trip_times[t.end_station_id].append(t)

    return trip_times

def classify_outliers(data, m=3, verbose=False): 
    ''' Just so that we can see more data about rejected outliers '''
    rejected = []
    kept = []

    mean = np.mean([t.duration().total_seconds() for t in data])
    std = np.std([t.duration().total_seconds() for t in data])
 
    for t in data:
        trip_time = t.duration().total_seconds()
        # Going to redo, only removing extrememly long trips and not extremely short trips?
        if trip_time - mean > m * std or t.end_date < t.start_date:
            rejected.append(t)
        else:
            kept.append(t)
    if verbose:
        after_mean = np.mean([t.duration().total_seconds() for t in kept])
        after_std = np.std([t.duration().total_seconds() for t in kept])


        print "Data mean before: %s, and after: %s" % (mean, after_mean)
        print "Data std before: %s, and after %s" % (std, after_std)
        print "Rejected:", len(rejected)
        #for r in rejected:
        #    print "\t",rejected
    return rejected

def reinsert_outliers(session):
    rem_type = session.query(TripType)\
        .filter(TripType.trip_type == 'Removed').first()
    for t in session.query(Trip)\
            .join(TripType, aliased=True)\
            .filter(TripType.id == rem_type.id).all():
        # The first week of every month is test
        # Just hard code it in for now
        if t.start_date.day < 8:
            t.trip_type_id = 3
        # Second week of every month is training
        else:
            t.trip_type_id = 1
        session.add(t)
    session.query(TripType).filter(TripType.id == rem_type.id).delete()
    session.commit()


def remove_outliers(session):
    s_ids = list(session.query(Station.id).all())
    count = 0
    new_trip_type = TripType("Removed")
    session.add(new_trip_type)
    for s_id in s_ids:
        trip_times = calc_outliers(session, s_id)
        for e_id, trips in trip_times.iteritems():
            rejected = classify_outliers(trips, verbose=False)
            for t in rejected:
                t.trip_type = new_trip_type
        session.commit()

        print "Finished station",s_id
        count += 1
        if count % 10 == 0:
            print "Finished with %s stations" % count

def main():
    session = Connector().getDBSession()
    #reinsert_outliers(session)
    remove_outliers(session)

if __name__ == '__main__':
    main()
