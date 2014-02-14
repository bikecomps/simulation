from models import * 
from utils import * 

import sys
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

    def generate_observations(self, start_d, normalize=False):
        '''
        Generates a day of observations based on the provided start_date
        
        Returns (key vector, observation vectors)
        '''
        s_ids = [s_id[0] for s_id in self.session.query(Station.id).all()]
        start_date = datetime.strptime(start_d, '%Y-%m-%d')
        all_obs = []

        # Not going to worry about clustering non stations
        zero_stations = []

        for s_id in s_ids:
            data_row = [0] * 24
            exp_lambdas = self.session.query(ExpLambda)\
                            .filter(ExpLambda.station_id == s_id)\
                            .filter(ExpLambda.year == start_date.year)\
                            .filter(ExpLambda.month == start_date.month)\
                            .filter(ExpLambda.is_week_day == (start_date.weekday() < 5))\
                            .all()
            if not len(exp_lambdas):
                zero_stations.append(s_id)
            else:
                for lam in exp_lambdas:
                    data_row[lam.hour] = 3600./lam.rate
                all_obs.append(data_row)

        for s_id in zero_stations:
            s_ids.remove(s_id)
        if normalize:
            all_obs = self.normalize(all_obs)
        return s_ids, all_obs

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

        if normalize:
            trip_counts = self.normalize_observations(trip_counts)

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

        print sum([sum(x) for x in total_vectors])
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
        centroids = {i:[x for x in xrange(len(s_ids)) if opt_clusters[x] == i] 
                        for i in xrange(max(opt_clusters) + 1)}
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
        # sanity test
        for c_id, cen in new_cs.iteritems():
            if sum(cen) != 1:
                print "Error, not equal to 1! %f" % sum(cen)
        return new_cs
    
    def dump_centroids_to_csv(self, centroids):
        if not len(centroids):
            return ''
        csv = 'cluster_id, ' + ','.join(map(str, xrange(len(centroids.values()[0])))) + '\n'
        for c, vec in centroids.iteritems():
            csv += str(c)+','+','.join(map(str, vec))+'\n'
        return csv

    def info_from_clusters(self, obs, s_ids, opt_clusters, centroids):
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
            sums = [0.]*len(centroids) 
            for i in xrange(len(centroids)):
                for o in range(len(obs)):
                    if o == c_id:
                        ob = obs[o]
                        for j in range(len(obs)):
                            # Only want to do from our rows to other rows
                            if opt_clusters[j] == i:
                                sums[i] += ob[j]
            data[c_id]['obs_sums'] = sums

            # Converts absolute sums to percentages of total
            sums_percentages = [x/float(sum(sums)) for x in sums]
            data[c_id]['obs_sums_percentages'] = sums_percentages

            # ASSUMES NORMALIZED CENTROIDS
            # Difference between centroid pairwise counts and observed pairwise counts 
            data[c_id]['percent_off'] = [x - y for x,y in zip(centroid_sums, sums_percentages)]
        
        return data

def trip_count_cluster():
    conn = Connector()
    s = conn.getDBSession()
    c = Clusterer(s)
    s_id_map, from_v, to_v, total_v = c.generate_trip_count_obs(conn, '2010-6-1', '2014-8-1', normalize=True)
    obs = total_v
    s_ids = sorted(s_id_map.iterkeys(), key=lambda k: s_id_map[k])
    opt_clusters = c.op_cluster_obs(obs, 5)
    centroids = c.get_centroids_from_clusters(s_ids, obs, opt_clusters)
    centroids = c.normalize_centroids(centroids)
    info = c.info_from_clusters(obs, s_ids, opt_clusters, centroids)
    for c_id, data in info.iteritems():
        print "-"*40,c_id,"-"*40
        for label, d in data.iteritems():
            print label+":",d

def hour_count_cluster():
    conn = Connector()
    c = Clusterer(s)
    s_ids, obs = c.generate_observations('2012-9-4')


def main():
    trip_count_cluster()
    return
    conn = Connector()
    s = conn.getDBSession()
    c = Clusterer(s)
    #print s_id_map, from_v, to_v, total_v
    #n = len(total_v)
    #s_ids, obs = c.generate_observations('2012-9-4')

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
