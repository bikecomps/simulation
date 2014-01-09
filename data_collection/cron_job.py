#! /usr/bin/env python

import urllib2
import csv
from datetime import datetime
from bs4 import BeautifulSoup

XML_URL = 'http://www.capitalbikeshare.com/data/stations/bikeStations.xml'

def parse_and_save(xml, csv_writer):
    now = datetime.now()
    data_soup = BeautifulSoup(xml, 'xml') 
    for station in data_soup.findAll('station'):
        station_id = station.terminalName.string
        num_bikes = station.nbBikes.string 
        num_empties = station.nbEmptyDocks.string
        csv_writer.writerow([now, station_id, num_bikes, num_empties])
       
def main():
    data = urllib2.urlopen(XML_URL).read()
    with open('bike_counts.csv', 'a') as csv_file:
        csv_writer = csv.writer(csv_file)
        parse_and_save(data, csv_writer)

if __name__ == "__main__":
    main()
