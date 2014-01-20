#! /usr/bin/env python

import urllib2
import csv
from datetime import datetime
from bs4 import BeautifulSoup
from models import *
from utils import *

XML_URL = 'http://www.capitalbikeshare.com/data/stations/bikeStations.xml'


def get_capital_xml():
    xml = urllib2.urlopen(XML_URL).read()
    return xml

def parse_xml(xml):
    '''
    Returns list of [station id, num_bikes, num_empties]
    '''
    station_statuses = []
    data_soup = BeautifulSoup(xml, 'xml') 
    for station in data_soup.findAll('station'):
        station_id = station.terminalName.string
        num_bikes = station.nbBikes.string 
        num_empties = station.nbEmptyDocks.string
        station_statuses.append([station_id, num_bikes, num_empties])
    return station_statuses


def parse_and_save(xml, csv_writer):
    '''
    Takes station statuses (bike counts) from xml and writes to a csv.
    '''
    now = datetime.now()
    data_soup = BeautifulSoup(xml, 'xml') 
    for station in data_soup.findAll('station'):
        station_id = station.terminalName.string
        num_bikes = station.nbBikes.string 
        num_empties = station.nbEmptyDocks.string
        csv_writer.writerow([now, station_id, num_bikes, num_empties])



def parse_and_save_to_db(session, xml):
    '''
    Takes xml and saves station statuses to db.
    '''
    stations = {s.id for s in session.query(Station)}
    now = datetime.datetime.now()
    data_soup = BeautifulSoup(xml, 'xml') 
    for station in data_soup.findAll('station'):
        station_id = int(station.terminalName.string)
        #print type(station_id)
        num_bikes = station.nbBikes.string 
        num_empties = station.nbEmptyDocks.string
        # Otherwise it's just an untracked station which we have no data for so we will ignore it
        if station_id in stations:
            session.add(StationStatus(station_id, now, num_bikes, num_empties))
        else:
            print "Error no station ",station_id

    session.commit()

def main():
    session = Connector().getDBSession()
    data = urllib2.urlopen(XML_URL).read()
    parse_and_save_to_db(session, data)

if __name__ == "__main__":
    main()
