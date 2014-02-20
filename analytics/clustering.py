from models import * 
from utils import * 

from datetime import timedelta
import sys
import itertools
import numpy as np
import Pycluster as pc
from scipy.cluster.vq import kmeans2
from datetime import datetime
import matplotlib.pyplot as plt
import json

def normalize_observations(obs):
    return [[x/float(sum(row)) if sum(row) > 0 else 0 for x in row] for row in obs]

def get_stations(conn, start_d=None, end_d=None):
    '''
    If a date range is supplied gets all stations (ids) that have recorded
    trips during that range. Otherwise, returns all stations (ids) in db.
    '''
    if start_d and end_d:
        query = """
                SELECT id FROM stations
                WHERE id IN  
                        (SELECT DISTINCT start_station_id
                         FROM trips
                         WHERE start_date BETWEEN '{s}' AND '{e}')
                AND id IN 
                        (SELECT DISTINCT end_station_id 
                         FROM trips 
                         WHERE start_date BETWEEN '{s}' AND '{e}')
                """.format(s=start_d, e=end_d)
    else:
        query = "SELECT id FROM stations"

    return [s_id[0] for s_id in conn.execute(query)]

def gen_hour_obs(conn, start_d, end_d, week_day=True, remove_zeroes=False):
    '''
    Generates a day of observations based on the provided start_date
    
    Returns (key vector, observation vectors)
    '''
    if remove_zeroes:
        s_ids = get_stations(conn, start_d, end_d)
    else:
        s_ids = get_stations(conn, start_d, end_d)

    s_id_map = {s_ids[i]:i for i in range(len(s_ids))}

    start_date = datetime.strptime(start_d, '%Y-%m-%d')
    end_date = datetime.strptime(end_d, '%Y-%m-%d')
    
    query = """
            SELECT start_station_id, end_station_id, 
                   EXTRACT(DOW FROM start_date), 
                   EXTRACT(HOUR FROM start_date),
                   COUNT(*)
            FROM trips 
            WHERE start_date BETWEEN '{s}' AND '{e}' 
            GROUP BY start_station_id, end_station_id,
                   EXTRACT(DOW FROM start_date), EXTRACT(HOUR FROM start_date);
            """.format(s=start_d, e=end_d)
    
    # Calculate the number of weekdays in a range, and weekend days
    # thanks http://stackoverflow.com/questions/3615375/python-count-days-ignoring-weekends
    day_generator = (start_date + timedelta(x + 1) for x in xrange((end_date - start_date).days + 1))
    num_weekdays = sum(day.weekday() < 5 for day in day_generator)
    num_weekend_days = (end_date - start_date).days - num_weekdays

    if week_day:
        day_range = range(1,6) 
    else:
        day_range = [0,6]

    departures = [[0] * 24 for s_id in s_ids]
    arrivals = [[0] * 24 for s_id in s_ids]

    # Normal: Departures
    for s_id, e_id, dow, hour, count in conn.execute(query):
        if dow in day_range:
            departures[s_id_map[s_id]][int(hour)] += count 
            arrivals[s_id_map[e_id]][int(hour)] += count 
    if week_day:
        num_days = num_weekdays
    else:
        num_days = num_weekend_days


    # Identify the stations with zero counts

    # Want averages
    departures = [[x/num_days for x in station] for station in  departures]
    arrivals = [[x/num_days for x in station] for station in arrivals]
    totals = [x + y for x,y in itertools.izip(departures, arrivals)]

    return s_ids, departures, arrivals, totals

def generate_trip_count_obs(eng, start_d, end_d, remove_zeroes=False):

    raw_query = """
            SELECT start_station_id, end_station_id, COUNT(*)
            FROM trips
            WHERE start_date BETWEEN '{s}' AND '{e}'
            GROUP BY start_station_id, end_station_id
            HAVING COUNT(*) > 0;
            """
    q = raw_query.format(s=start_d, e=end_d) 
    rows = list(eng.execute(q))

    # Gives ability to cluster 
    if remove_zeroes:
        s_ids = get_stations(eng, start_d, end_d)
    else:
        s_ids = get_stations(eng, start_d, end_d)

    s_id_map = {s_ids[i]:i for i in range(len(s_ids))}

    ## Rather than query directly for stations, just get them from our original query
    #unique_start_stations = {row[0] for row in rows}
    #unique_end_stations = {row[1] for row in rows}
    #s_ids = sorted(list(unique_start_stations.union(unique_end_stations)))
    #s_id_map = {s_ids[i]:i for i in xrange(len(s_ids))}

    trip_counts = [[0]*len(s_ids) for x in xrange(len(s_ids))]
    for s_id, e_id, c in rows:
        trip_counts[s_id_map[s_id]][s_id_map[e_id]] = c 

    n = len(trip_counts)
    
    # Three vectors, a from->to, a to<-from, and a total
    from_vectors = trip_counts
    to_vectors = [[trip_counts[j][i] for i in xrange(n)] for j in xrange(n)]

    total_vectors = [[0] * n for x in xrange(n)]
    for i in xrange(n):
        for j in xrange(n):
            if i != j:
                total_vectors[i][j] = to_vectors[i][j] + from_vectors[i][j]
            # Don't double up on self loops
            else:
                total_vectors[i][j] = to_vectors[i][j]

    return s_id_map, from_vectors, to_vectors, total_vectors            

def cluster_obs(obs, k):
    obs = np.array(obs)
    return kmeans2(obs, k)


def op_cluster_obs(obs, max_k=30, npass=10):
    ''' 
    Info on pycluster available here:
         http://bonsai.hgc.jp/~mdehoon/software/cluster/cluster.pdf 
    '''

    obs = np.vstack(obs)
    # Minus 2 for at least two clusters
    errors = [0] * (max_k - 1)
    labels = [None] * (max_k - 1)

    # Doesn't make any sense for clusters = 1
    for i in xrange(2, max_k + 1):
        label, error, nfound = pc.kcluster(obs, i, npass=npass)
        errors[i - 2] = error
        labels[i - 2] = label
        

    # Find "kink" in error -> length is 1 less than errors
    error_deriv = [errors[i] - errors[i-1] for i in range(1, len(errors))]
    
    # Want to maximize difference of the two slopes
    opt_diff = -1
    opt_i = -1

    n = len(error_deriv)
    for i in range(1, n): 
        # Approximate the slope of the derivative
        diff = abs(sum(error_deriv[0:i])/i - sum(error_deriv[i:])/(n-i))
        if diff > opt_diff:
            opt_diff = diff
            opt_i = i 

    return labels[opt_i]

def clusters_to_coords(session, id_key, clusters):
    csv = "s_id, name, lat, lon, cluster\n"
    for i in xrange(len(id_key)):
        s = session.query(Station).filter(Station.id == id_key[i]).first()
        lat = s.intersection.lat
        lon = s.intersection.lon
        csv += "%s, \"%s\", %f, %f, %d\n" % (id_key[i], s.name, lat, lon, clusters[i])
    return csv
    
def get_centroids_from_clusters(s_ids, obs, opt_clusters):
    # Get the stations associated with every centroid
    centroids = {i:[x for x in xrange(len(s_ids)) if opt_clusters[x] == i] 
                    for i in xrange(max(opt_clusters) + 1)}
    # cluster points are indices of station_ids in s_ids list
    for c, cluster_points in centroids.iteritems():
        com_vecs = [obs[i] for i in cluster_points]
        sum_vec = reduce(lambda x, y: [x[i]+y[i] for i in xrange(len(x))],
                         com_vecs, [0]*len(com_vecs[0]))
        centroid = [x/float(len(cluster_points)) for x in sum_vec]
        centroids[c] = centroid
    return centroids

def normalize_centroids(centroids):
    return {c_id:[x/sum(cen) for x in cen] 
            for c_id, cen in centroids.iteritems()}

def dump_centroids_to_csv(centroids):
    if not len(centroids):
        return ''
    csv = 'cluster_id, ' + ','.join(map(str, xrange(len(centroids.values()[0])))) + '\n'
    for c, vec in centroids.iteritems():
        csv += str(c)+','+','.join(map(str, vec))+'\n'
    return csv

def info_from_hour_clusters(raw_obs, obs, s_ids, opt_clusters, centroids):
    data = {c_id:{} for c_id in centroids.iterkeys()}
    for c_id,vec in centroids.iteritems():
        # Stations in this cluster
        data[c_id]['stations'] = [s_ids[i] for i in xrange(len(opt_clusters)) if opt_clusters[i] == c_id]

        # Number of stations in the cluster
        data[c_id]['num_stations'] = len(data[c_id]['stations'])

    return data

def info_from_trip_clusters(raw_obs, obs, s_ids, opt_clusters, centroids):
    data = {c_id:{} for c_id in centroids.iterkeys()}
    for c_id,vec in centroids.iteritems():
        # Sums pairwise of observations from cluster to all other cluster
        centroid_sums = [sum([vec[i] for i in xrange(len(vec)) if opt_clusters[i] == j]) for j in xrange(len(centroids))]
        data[c_id]['centroid_sums'] = centroid_sums

        # Stations in this cluster
        data[c_id]['stations'] = [s_ids[i] for i in xrange(len(opt_clusters)) if opt_clusters[i] == c_id]

        # Number of stations in the cluster
        data[c_id]['num_stations'] = len(data[c_id]['stations'])

        # Sums pairwise of observations from this cluster (row) to others (columns)
        # Only makes sense on unnormalized obs
        sums = [0.]*len(centroids) 
        # Get the total number of trips between each cluster
        for o in range(len(raw_obs)):
            # Row corresponds to station in our current cluster
            if opt_clusters[o] == c_id: 
                ob = obs[o]
                for j in range(len(ob)):
                    # Get the index from opt_clusters for this particular column
                    sums[opt_clusters[j]] += ob[j]
        data[c_id]['obs_sums'] = sums

        # Converts absolute sums to percentages of total
        sums_percentages = [x/float(sum(sums)) for x in sums]
        data[c_id]['obs_sums_percentages'] = sums_percentages
        ''' Me being dumb 
        # Sums pairwise of observations from this cluster (row) to others (columns)
        sums = [0.]*len(centroids) 
        # Corresponds to s_ids
        for o in range(len(obs)):
            # Row corresponds to station in our current cluster
            if opt_clusters[o] == c_id: 
                ob = obs[o]
                print "Test", c_id, o, ob
                for j in range(len(ob)):
                    # Get the index from opt_clusters for this particular column
                    sums[opt_clusters[j]] += ob[j]
        data[c_id]['obs_sums'] = sums

        # Converts absolute sums to percentages of total
        sums_percentages = [x/float(sum(sums)) for x in sums]
        data[c_id]['obs_sums_percentages'] = sums_percentages

        # ASSUMES NORMALIZED CENTROIDS
        # Difference between centroid pairwise counts and observed pairwise counts 
        data[c_id]['percent_off'] = [x - y for x,y in zip(centroid_sums, sums_percentages)]
        '''
    
    return data

def get_clusters_as_dict(cluster_type):
    if cluster_type == "Trip counts":
        return trip_count_cluster()
    elif cluster_type == "Hours of high traffic":
        return hour_count_cluster()
    else:
        return {}

def get_clusters(cluster_type):
    return dump_json(get_clusters_as_dict(cluster_type))
        
def dump_json(to_dump):
    '''
    Utility to dump json in nice way
    '''
    return json.dumps(to_dump, indent=4, default=json_dump_handler)
    
def json_dump_handler(obj):
    '''
    Converts from python to json for some types, add more ifs for more cases

    Thanks to following site:
    http://stackoverflow.com/questions/455580/json-datetime-between-python-and-javascript
    '''
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    else:
        raise TypeError, 'Cannot serialize item %s of type %s' % (repr(obj), type(obj))


def trip_count_cluster(start_d, end_d, normalize=True, cluster_empties=False, choice="totals",
                       max_k=5):
    conn = Connector()
    engine = conn.getDBEngine()

    s_id_map, from_v, to_v, total_v = generate_trip_count_obs(engine, start_d, end_d, remove_zeroes=(not cluster_empties))
    orig_from, orig_to, orig_total = from_v, to_v, total_v
    if normalize:
        from_v = normalize_observations(from_v)
        to_v = normalize_observations(to_v)
        total_v = normalize_observations(total_v)

    if choice == "totals":
        obs = total_v
        raw_obs = orig_total
    elif choice == "departures":
        obs = from_v
        raw_obs = orig_total
    elif choice == "arrivals":
        obs = to_v
        raw_obs = orig_total

    s_ids = sorted(s_id_map.iterkeys(), key=lambda k: s_id_map[k])
    opt_clusters = op_cluster_obs(obs, max_k)
    centroids = get_centroids_from_clusters(s_ids, obs, opt_clusters)
    centroids = normalize_centroids(centroids)
    info = info_from_trip_clusters(raw_obs, obs, s_ids, opt_clusters, centroids)

    clusters_dict = {}
    for c_id, data in info.iteritems():
        clusters_dict[c_id] = data["stations"]
    return clusters_dict

def hour_count_cluster(start_d, end_d, normalize=True, cluster_empties=False,
                       choice="departures", max_k=8):
    conn = Connector()
    engine = conn.getDBEngine()
    s_ids, departures, arrivals, totals = gen_hour_obs(engine, start_d, end_d, remove_zeroes=(not cluster_empties))
    orig_deps, orig_arrs, orig_tots = departures, arrivals, totals

    if normalize:
        departures = normalize_observations(departures)
        arrivals = normalize_observations(arrivals)
        totals = normalize_observations(totals)

    if choice == "totals":
        obs = total_v
        raw_obs = orig_tots
    elif choice == "departures":
        obs = departures 
        raw_obs = orig_deps
    elif choice == "arrivals":
        obs = to_v
        raw_obs = orig_arrs

    opt_clusters = op_cluster_obs(obs, max_k)
    centroids = get_centroids_from_clusters(s_ids, obs, opt_clusters)
    centroids = normalize_centroids(centroids)
    #print dump_centroids_to_csv(centroids)
    #print "\n\n\n"
    info = info_from_hour_clusters(raw_obs, obs, s_ids, opt_clusters, centroids)
    #for c_id, data in info.iteritems():
    #    print "-"*40,c_id,"-"*40
    #    for label, d in data.iteritems():
    #        print label+":",d

    clusters_dict = {}
    for c_id, data in info.iteritems():
        clusters_dict[c_id] = data["stations"]
    return clusters_dict


def main():
    print hour_count_cluster('2012-05-01', '2012-06-1') 
    print trip_count_cluster('2012-05-01', '2012-06-1')
    return
    conn = Connector()
    s = conn.getDBSession()
    c = Clusterer(s)
    #print s_id_map, from_v, to_v, total_v
    #n = len(total_v)
    #s_ids, obs = c.gen_hour_obs('2012-9-4')

    #opt_clusters = c.op_cluster_obs(obs, 10)
    #centroids = c.get_centroids_from_clusters(s_ids, obs, opt_clusters)
    n = len(centroids.values()[0])
    fig, ax = plt.subplots()
    width = .35
    ind = np.arange(n)
    print ind + width
    colors = ['r','g','b','c','m','k','w','y']
    for c, vec in centroids.iteritems():
        ax.bar(ind + width*c + 1, vec, width, color=colors[c])
    ax.set_ylabel("Percentage of trips")
    ax.set_xlabel("Hour")

    plt.show() 

    #c.clusters_to_coords(s, s_ids, opt_clusters)
    #centroids, labels = c.cluster_obs(obs, 5)
    #print centroids, labels


if __name__ == '__main__':
    main()
