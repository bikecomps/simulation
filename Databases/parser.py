'''
Simple parser to read in specific CSVs/XML files related to 
Capital Bikeshare. Parses and inserts into the DB structure.
Assumes valid DB arguments

Usage: python parser.py <-t | -ot | -s> <filename>

Options:
        -t: file is a trips file (capitalbikeshare) with post 2011 format
        -ot: file is a trips file (capitalbikeshare) from 2010-2011
        -s: file is a stations XML file (capitalbikeshare)
'''

from bs4 import BeautifulSoup
import csv
import re
import sys

DB_NAME = 'TODO'
TRIP_DB_NAME = 'TODO'
STATION_DB_NAME = 'TODO'

# Before 2012 dumps terminal data is stored in start/end station fields (not own)
def parse_bike_trips(input_filename):
    '''
    Parses capitalbikeshare trip csvs using 2012+ format.
    '''
    with open(input_filename) as csv_file:
        reader = csv.reader(csv_file)
        headers = next(reader, None)
        for row in reader:
            start_time = row[1]
            end_time = row[4]

            start_station_id = row[3]
            end_station_id = row[6]
            
            bike_id = row[7]
            rider_type = "Registered" if row[8] == "Subscriber" else row[8]
            
            # insert into DB
            print start_time, end_time, start_station_id, end_station_id, bike_id, rider_type
            
def parse_old_bike_trips(input_filename):
    '''
    Parses capitalbikeshare trip csvs using 2010-2011 format.
    '''
    reg_station_id = r'\((\d+)\)'
    with open(input_filename) as csv_file:
        reader = csv.reader(csv_file)
        headers = next(reader, None)
        for row in reader:
            start_time, end_time = row[1:3]
            bike_id = row[5]
            rider_type = row[6]
        
            # The terminal id's are stored within a longer string, we only want the ids
            start_station = re.search(reg_station_id, row[3])
            end_station = re.search(reg_station_id, row[4])

            if start_station == None or end_station == None:
                print "Invalid row: %s"  %  row
                continue
                
            # Rip off the parentheses
            start_station_id = start_station.group(1)
            end_station_id = end_station.group(1)

            # Insert into DB
            print start_time, end_time, start_station_id, end_station_id, bike_id, rider_type
                    
def parse_stations(input_filename):
    '''
    Parses capitalbikeshare station XMLs.
    '''
    f = open(input_filename)
    raw_xml = f.read()
    f.close()
    
    soup = BeautifulSoup(raw_xml)
    for station in soup.findAll('station'):
        station_id = int(station.terminalname.string)
        name = station.find('name').string
        lat = float(station.lat.string)
        lon = float(station.long.string)
        capacity = int(station.nbbikes.string) + int(station.nbemptydocks.string)
        
        # Save to DB
        print station_id, name, lat, lon, capacity


def main():
    parse_options = {
            '-t' : parse_bike_trips,
            '-to' : parse_old_bike_trips,
            '-s' : parse_stations
    }

    parse_options[sys.argv[1]](sys.argv[2])


if __name__ == '__main__':
    main()
