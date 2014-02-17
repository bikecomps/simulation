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

class Clusterer:

    def __init__(self, session):
        self.session = session

    def normalize_observations(self, obs):
        return [[x/float(sum(row)) if sum(row) > 0 else 0 for x in row] for row in obs]

    def gen_hour_obs(self, conn, start_d, end_d, week_day=True):
        '''
        Generates a day of observations based on the provided start_date
        
        Returns (key vector, observation vectors)
        '''
        s_ids = [s_id[0] for s_id in self.session.query(Station.id).all()]
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

        # Want averages
        departures = [[x/num_days for x in station] for station in  departures]
        arrivals = [[x/num_days for x in station] for station in arrivals]
        totals = [x + y for x,y in itertools.izip(departures, arrivals)]

        return s_ids, departures, arrivals, totals

    def generate_trip_count_obs(self, conn, start_d, end_d, normalize=False):
        session = conn.getDBSession()
        eng = conn.getDBEngine()

        raw_query = """
                SELECT start_station_id, end_station_id, COUNT(*)
                FROM trips
                WHERE start_date BETWEEN '{s}' AND '{e}'
                      AND trip_type_id=1
                GROUP BY start_station_id, end_station_id
                HAVING COUNT(*) > 0;
                """
        q = raw_query.format(s=start_d, e=end_d) 
        rows = list(eng.execute(q))

        # Rather than query directly for stations, just get them from our original query
        unique_start_stations = {row[0] for row in rows}
        unique_end_stations = {row[1] for row in rows}
        s_ids = sorted(list(unique_start_stations.union(unique_end_stations)))
        s_id_map = {s_ids[i]:i for i in xrange(len(s_ids))}

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

    def cluster_obs(self, obs, k):
        obs = np.array(obs)
        return kmeans2(obs, k)

    def op_cluster_obs(self, obs, max_k=30, npass=10):
        ''' 
        Info on pycluster available here:
             http://bonsai.hgc.jp/~mdehoon/software/cluster/cluster.pdf 
        '''

        obs = np.vstack(obs)
        min_error = sys.maxint
        best_clustering = []

        for i in xrange(1, max_k):
            labels, error, nfound = pc.kcluster(obs, i, npass=npass)

            if error < min_error:
                min_error = error
                best_clustering = labels

        return best_clustering

    def clusters_to_coords(self, session, id_key, clusters):
        csv = "s_id, name, lat, lon, cluster\n"
        for i in xrange(len(id_key)):
            s = session.query(Station).filter(Station.id == id_key[i]).first()
            lat = s.intersection.lat
            lon = s.intersection.lon
            csv += "%s, \"%s\", %f, %f, %d\n" % (id_key[i], s.name, lat, lon, clusters[i])
        return csv
        
    def get_centroids_from_clusters(self, s_ids, obs, opt_clusters):
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
    
    def normalize_centroids(self, centroids):
        new_cs = {c_id:[x/sum(cen) for x in cen] #return 
                for c_id, cen in centroids.iteritems()}
        return new_cs
    
    def dump_centroids_to_csv(self, centroids):
        if not len(centroids):
            return ''
        csv = 'cluster_id, ' + ','.join(map(str, xrange(len(centroids.values()[0])))) + '\n'
        for c, vec in centroids.iteritems():
            csv += str(c)+','+','.join(map(str, vec))+'\n'
        return csv

    def info_from_hour_clusters(self, raw_obs, obs, s_ids, opt_clusters, centroids):
        data = {c_id:{} for c_id in centroids.iterkeys()}
        for c_id,vec in centroids.iteritems():
            # Stations in this cluster
            data[c_id]['stations'] = [s_ids[i] for i in xrange(len(opt_clusters)) if opt_clusters[i] == c_id]

            # Number of stations in the cluster
            data[c_id]['num_stations'] = len(data[c_id]['stations'])

        return data

    def info_from_trip_clusters(self, raw_obs, obs, s_ids, opt_clusters, centroids):
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

def trip_count_cluster():
    normalize = False
    conn = Connector()
    s = conn.getDBSession()
    c = Clusterer(s)
    s_id_map, from_v, to_v, total_v = c.generate_trip_count_obs(conn, '2010-5-1', '2013-6-30')
    orig_from, orig_to, orig_total = from_v, to_v, total_v
    if normalize:
        from_v = self.normalize_observations(from_v)
        to_v = self.normalize_observations(to_v)
        total_v = self.normalize_observations(total_v)


    obs = total_v
    raw_obs = orig_total

    s_ids = sorted(s_id_map.iterkeys(), key=lambda k: s_id_map[k])
    opt_clusters = c.op_cluster_obs(obs, 5)
    centroids = c.get_centroids_from_clusters(s_ids, obs, opt_clusters)
    centroids = c.normalize_centroids(centroids)
    info = c.info_from_trip_clusters(raw_obs, obs, s_ids, opt_clusters, centroids)
    for c_id, data in info.iteritems():
        print "-"*40,c_id,"-"*40
        for label, d in data.iteritems():
            print label+":",d

def hour_count_cluster():   
    normalize = False
    conn = Connector()
    engine = conn.getDBEngine()
    s = conn.getDBSession()
    c = Clusterer(s)
    s_ids, departures, arrivals, totals = c.gen_hour_obs(engine, '2013-5-1', '2013-6-1')
    orig_deps, orig_arrs, orig_tots = departures, arrivals, totals

    if normalize:
        departures = self.normalize_observations(departures)
        arrivals = self.normalize_observations(arrivals)
        totals = self.normalize_observations(totals)

    obs = departures
    raw_obs = orig_deps

    opt_clusters = c.op_cluster_obs(obs, 5)
    centroids = c.get_centroids_from_clusters(s_ids, obs, opt_clusters)
    centroids = c.normalize_centroids(centroids)
    print c.dump_centroids_to_csv(centroids)
    print "\n\n\n"
    info = c.info_from_hour_clusters(raw_obs, obs, s_ids, opt_clusters, centroids)
    for c_id, data in info.iteritems():
        print "-"*40,c_id,"-"*40
        for label, d in data.iteritems():
            print label+":",d

def main():
    hour_count_cluster() 
    #trip_count_cluster()
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
