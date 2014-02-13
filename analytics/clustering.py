from models import * 
from utils import * 

import sys
import numpy as np
import Pycluster as pc
from scipy.cluster.vq import kmeans2
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

class Clusterer:

    def __init__(self, session):
        self.session = session

    def generate_prob_observations(self, start_d):
        '''
        Generates a day of observations based on provided date based on the percentage
        of when the various trips are.
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
                    data_row[lam.hour] = lam.rate

                total_avg = float(sum(data_row))
                data_row = [x/total_avg for x in data_row]
                all_obs.append(data_row)

        for s_id in zero_stations:
            s_ids.remove(s_id)
        return s_ids, all_obs


    def generate_observations(self, start_d):
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
                    data_row[lam.hour] = lam.rate
                all_obs.append(data_row)

        for s_id in zero_stations:
            s_ids.remove(s_id)
        return s_ids, all_obs

    def generate_trip_count_obs(self, conn, start_d, end_d):
        session = conn.getDBSession()
        eng = conn.getDBEngine()
        s_ids = [s_id[0] for s_id in self.session.query(Station.id).all()]

        raw_query = """
                SELECT start_station_id, end_station_id, COUNT(*)
                FROM trips
                WHERE start_date BETWEEN '{s}' AND '{e}'
                      AND trip_type_id=1
                GROUP BY start_station_id, end_station_id
                """
        q = raw_query.format(s=start_d, e=end_d) 
        print "Q?"
        print q
        print "DoNE?"
        rows = list(eng.execute(q))

        #trip_counts = [[0]*len(s_ids) for x in range(len(s_ids))]
        trip_counts = {s_id:{s_id:0} for s_id in s_ids}
        for s_id, e_id, c in rows:
            trip_counts[s_id][e_id] = c 

    def cluster_obs(self, obs, k):
        obs = np.array(obs)
        return kmeans2(obs, k)

    def op_cluster_obs(self, obs, max_k=30):
        ''' 
        Info on pycluster available here:
             http://bonsai.hgc.jp/~mdehoon/software/cluster/cluster.pdf 
        '''

        obs = np.vstack(obs)
        min_error = sys.maxint
        best_clustering = []

        for i in xrange(1, max_k):
            labels, error, nfound = pc.kcluster(obs, i)

            if error < min_error:
                min_error = error
                best_clustering = labels
        return best_clustering

    def clusters_to_coords(self, session, id_key, clusters):
        print "s_id, lat, lon, cluster"
        for i in xrange(len(id_key)):
            s = session.query(Station).filter(Station.id == id_key[i]).first()
            lat = s.intersection.lat
            lon = s.intersection.lon
            print "%s, %s, %f, %f, %d" % (id_key[i], s.name, lat, lon, clusters[i])
        
    def get_centroids_from_clusters(self, s_ids, obs, opt_clusters):
        centroids = {i:[x for x in range(len(s_ids)) if opt_clusters[x] == i] for i in range(max(opt_clusters) + 1)}
        for c, cluster_points in centroids.iteritems():
            com_vecs = [obs[i] for i in cluster_points]
            sum_vec = reduce(lambda x, y: [x[i]+y[i] for i in range(len(x))] ,com_vecs, [0]*len(com_vecs[0]))
            centroid = [x/float(len(cluster_points)) for x in sum_vec]
            centroids[c] = centroid
        return centroids

def main():
    conn = Connector()
    s = conn.getDBSession()
    c = Clusterer(s)
    c.generate_trip_count_obs(conn, '2012-6-1', '2012-8-1')
    return
    #s_ids, obs = c.generate_observations('2012-9-4')
    s_ids, obs = c.generate_prob_observations('2012-9-4')

    opt_clusters = c.op_cluster_obs(obs, 5)
    centroids = c.get_centroids_from_clusters(s_ids, obs, opt_clusters)
    for c, vec in centroids.iteritems():
        print c, vec
   
    n = len(centroids)
    fig, ax = plt.subplot()
    ind = np.arrange(n)
    width = .2
    colors = ['r','g','b','o','p','w','y']
    for c, vec in centroids.iteritems():
        ax.bar(ind + .2*c, vec, width, color=colors[c])
    plt.show() 

    #c.clusters_to_coords(s, s_ids, opt_clusters)
    #centroids, labels = c.cluster_obs(obs, 5)
    #print centroids, labels


if __name__ == '__main__':
    main()
