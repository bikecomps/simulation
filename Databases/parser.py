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

#from BeautifulSoup import BeautifulStoneSoup
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

            start_station = row[3]
            end_station = row[6]
            
            bike_id = row[7]
            rider_type = row[8]
            
            # Add to DB
            
def parse_old_bike_trips(input_filename):
	'''
	Parses capitalbikeshare trip csvs using 2010-2011 format.
	'''
	search_str = re.compile('\(\d+\)')
	
	with open(input_filename) as csv_file:
		reader = csv.reader(csv_file)
		headers = next(reader, None)
		for row in reader:
			start_time, end_time = row[1:3]
			bike_id = row[5]
			rider_type = row[6]

			# The terminal id's are stored within a longer string, we only want the ids
			start_station = search_str.search(row[3])
			end_station = search_str.search(row[4])

			if start_station == None or end_station == None:
				print "Invalid row: %s"  %  row
				continue

			# Rip off the parentheses
			start_station = start_station.group()[1:-1] 
			end_station = end_station.group()[1:-1]
			print start_time, end_time, start_station, end_station

			# Insert into DB

def parse_stations(input_filename):
    '''
    Parses capitalbikeshare station XMLs.
    '''
    f = open(input_filename)
    raw_xml = f.read()
    f.close()
    
    soup = BeautifulStoneSoup(raw_xml)
    for station in soup.findAll('station'):
        station_attrs = dict(station.attrs)
        
        station_id = station_attrs['terminalName']
        name = station_attrs['name']
        lat = station_attrs['lat']
        lon = station_attrs['long']
        
        capacity = int(station_attrs['nbBikes']) + int(station_attrs['nbEmptyDocks'])
        
        # Save to DB


def main():
    parse_options = {
            '-t' : parse_bike_trips,
            '-to' : parse_old_bike_trips,
            '-s' : parse_stations
    }

    parse_options[sys.argv[1]](sys.argv[2])


if __name__ == '__main__':
	main()
