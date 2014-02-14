#!/usr/bin/python
'''
Simple parser to read in specific CSVs/XML files related to 
Capital Bikeshare. Parses and inserts into the DB structure
or to a CSV file.
Assumes valid DB arguments.

Before inserting trips into database, make sure to insert
ALL stations because of foreign key constraints on
the start and end stations of every trip.

Usage: python parser.py -t | -to | -s filename

Options:
        -t: file is a trips file (capitalbikeshare) with post 2011 format
        -to: file is a trips file (capitalbikeshare) from 2010-2011
        -s: file is a stations XML file (capitalbikeshare)
'''

from bs4 import BeautifulSoup
import csv
import re
import sys
import datetime

from utils import Connector
from models import *

CSV_WRITER = False

def write_to_csv(input_filename, header, data):
    '''
    Write out data into a new csv file
    '''
    out_file = open(re.sub(r'(\.csv)|(\.xml)', '.out.csv', input_filename), 'w')
    csv_out_file = csv.writer(out_file)
    # write header
    csv_out_file.writerow(header)

    for line_data in data:
        csv_out_file.writerow(line_data)

    out_file.close()

# Before 2012 dumps terminal data is stored in start/end station fields (not own)
def parse_bike_trips(input_filename ):
    '''
    Parses capitalbikeshare trip csvs using 2012+ format.
    '''

    data = []
    with open(input_filename) as csv_file:
        reader = csv.reader(csv_file)
        headers = next(reader, None)

        for row in reader:
            if len(row) < 9: continue
            try:
                start_time = row[1]
                end_time = row[4]

                start_station_id = int(row[3])
                end_station_id = int(row[6])
                
                bike_id = row[7]
                rider_type = "Registered" if row[8] == "Subscriber" else row[8]

                # 'ExtrapolationTesting' -> 8
                data.append([bike_id, rider_type, 8, start_time, end_time, start_station_id, end_station_id])
            except ValueError:
                print "Error on row %s", row
                
    return (["Bike Id", "Rider Type", "Trip Type", "Start Time", "End Time", 
            "Start Station", "End Station"],data)
#except ValueError:
#    print "Invalid input row, skipping %s" % row

def parse_old_bike_trips(input_filename):
    '''
    Parses capitalbikeshare trip csvs using 2010-2011 format.
    '''
    data = []

    reg_station_id = r'\((\d+)\)'
    with open(input_filename) as csv_file:
        reader = csv.reader(csv_file)
        headers = next(reader, None)
        for row in reader:
            start_time, end_time = row[1:3]
            bike_id = row[5]
            rider_type = row[6]
        
            # The terminal id's are stored within a longer string, we only want the ids
            start_station = int(re.search(reg_station_id, row[3]))
            end_station = int(re.search(reg_station_id, row[4]))

            if start_station == None or end_station == None:
                print "Invalid row: %s"  %  row
                continue
                
            # Rip off the parentheses
            start_station_id = int(start_station.group(1))
            end_station_id = int(end_station.group(1))
            data.append([bike_id, rider_type, 'Training', start_time, end_time, start_station_id, 
                         end_station_id])
    return (["Bike Id", "Rider Type", "Trip Type", "Start Time", "End Time", 
            "Start Station", "End Station"],data)
  
def parse_stations(input_filename):
    '''
    Parses capitalbikeshare station XMLs.
    '''
    f = open(input_filename)
    raw_xml = f.read()
    f.close()
    
    soup = BeautifulSoup(raw_xml, 'xml')
    data = []

    for station in soup.findAll('station'):
        station_id = int(station.terminalName.string)
        name = station.find('name').string
        lat = float(station.lat.string)
        lon = float(station.long.string)
        capacity = int(station.nbBikes.string) + int(station.nbEmptyDocks.string)
        
        data.append([station_id, name, lat, lon, capacity])

    return (['Station Id', 'Name', 'Latitude', 'Longitude', 'Capacity'],
            data)

def main():
    parse_options = {
            '-t' : parse_bike_trips,
            '-to' : parse_old_bike_trips,
            '-s' : parse_stations
    }
    
    headers, data = parse_options[sys.argv[1]](sys.argv[2])

    if CSV_WRITER:
        write_to_csv(sys.argv[2], 
                     headers, 
                     data)
    else:
        c = Connector()
        session = c.getDBSession()
        
        if sys.argv[1] == '-s':
            default_neigh = Neighborhood(-1)
            session.add(default_neigh)

            for line in data:
                intersection = Intersection(line[2], line[3], default_neigh)
                session.add(intersection)
                session.add(Station(line[0], line[1],line[4], intersection))
        else:
            for line in data:
                if session.query(Station).filter(Station.id == line[5]).first() == None or session.query(Station).filter(Station.id == line[6]).first() == None:
                    print "Invalid station, skipping"
                else:
                    session.add(Trip(line[0], line[1], line[2], datetime.datetime.strptime(line[3], "%m/%d/%Y %H:%M"),
                                 datetime.datetime.strptime(line[4], "%m/%d/%Y %H:%M"), line[5], line[6]))
        # commit to DB
        print "Preparing to commit"
        session.commit()

if __name__ == '__main__':
	main()
