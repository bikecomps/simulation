import re
import os
from collections import defaultdict

def parse_old(filename):
    lines = read(filename)
    station_to_name = defaultdict(set)
    regex = re.compile(r'\((\d+)\)')

    num = 0
    for row in lines:
        if num == 0:
            num += 1
            continue 

        ss_id = regex.search(row[3])
        es_id = regex.search(row[4])

        if not ss_id or not es_id:
            print "Invalid row"
            continue
        ss_id = ss_id.group(0)
        es_id = es_id.group(0)

        ss_name = regex.sub('', row[3])
        es_name = regex.sub('', row[4])

        station_to_name[ss_id].add(ss_name)
        station_to_name[es_id].add(es_name)

    return station_to_name
 
def parse_mid(filename):
    lines = read(filename)
    station_to_name = defaultdict(set)
    regex = re.compile(r'\((\d+)\)')

    num = 0
    for row in lines:
        if num == 0:
            num += 1
            continue 

        try:
            ss_id = int(row[4])
            ss_name = row[3]

     
            es_id = int(row[7])
            es_name = row[6]

            station_to_name[ss_id].add(ss_name)
            station_to_name[es_id].add(es_name)
        except ValueError:
            print "Error"

    return station_to_name
 

def parse_new(filename):
    lines = read(filename)
    station_to_name = defaultdict(set)
    regex = re.compile(r'\((\d+)\)')

    num = 0
    for row in lines:
        if num == 0:
            num += 1
            continue 

        try:
            ss_id = int(row[3])
            ss_name = row[2]

     
            es_id = int(row[6])
            es_name = row[5]

            station_to_name[ss_id].add(ss_name)
            station_to_name[es_id].add(es_name)
        except ValueError:
            print "Error"

    return station_to_name
 

def read(filename):
    with open(filename, 'r') as f:
        return [line.split(',') for line in f.readlines()]
    return []

def parse_to_name(filename):
    with open(filename, 'r') as f:
        lines = [line.split(',') for line in f.readlines()]
                 

def check_folder(foldername, fun):
    all = defaultdict(set)
    for root, d, files in os.walk(foldername):
        for fname in files:
            info = fun(os.path.join(root, fname))
            for id, names in info.iteritems():
                all[id].update(names)
    bad_results = [(id, names) for id, names in all.iteritems() if len(names) > 1]
    print bad_results

def main():
    #results = parse_old("/data/OldCapitalTrips/2010-4th-quarter.csv")
    #bad_results = [(id, names) for id, names in results.iteritems() if len(names) > 1]
    #print bad_results
    #check_folder("/data/OldCapitalTrips", parse_old)
    #check_folder("/data/MidCapitalTrips", parse_mid)
    check_folder("/data/NewCapitalTrips", parse_new)

    
if __name__ == '__main__':
    main()
