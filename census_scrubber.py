import requests
import traceback
import json
import re
import sys
from functools import partial
from data_model import *
from utility import Connector


'''
Notes on first run:
-> ALTER TABLE intersections DROP CONSTRAINT intersections_neighborhood_id_fkey;
-> Do stuff
-> ALTER TABLE intersections ADD CONSTRAINT intersections_neighborhood_id_fkey FOREIGN KEY (neighborhood_id) REFERENCES neighborhoods ON DELETE CASCADE;

Other Notes:
FIPS code structure:
2 digits - State
3 digits - County
6 digits - Census Tract
4 digits - Census Block
'''
CREATED_TABLE_SUMMARY = 'summary.txt'

# Ignoring if lat/long on a border
API_URL = 'http://data.fcc.gov/api/block/%i/find?format=%s&latitude=%s&longitude=%s&showall=false'
JSON = 'json'
XML = 'xml'


# (State, Summary Level, State, Table Code)
CENSUS_URL = 'http://censusdata.ire.org/%i/all_%i_in_%i.%s.csv'

# Just various codes from http://census.ire.org/data/bulkdata.html
DC_CODE = 11
TRACT_DETAIL = 140
CENSUS_HEADER_FORMAT = r'[A-Z]\d+'
CENSUS_TABLES = [
        'P1',  # Total Population
        'P3',  # Race
        'P12', # Sex
        'P18', # Household Type
        'H13', # Household Size
        'H2'   # Urban and Rural
    ]


def request_census_block(lat, lon, year=2010, form=JSON): 
    '''
    Returns the US Census Bureau Block number (15 char. FIPS code)
    given the provided lat/long

    Based on FCC API:
         http://www.fcc.gov/developers/census-block-conversions-api
    '''
    request_url = API_URL % (year, form, lat, lon)  
    reply = requests.get(request_url)
    return reply.json()


def create_known_neighborhoods(session):
    '''
    For now we'll just print out the FIPS for each station
    eventually put it back into the DB in a new column (neighborhood?)
    '''
    intersections = session.query(Intersection)
    visited_FIPS = set()

    for inter_x in intersections:
        census_json = request_census_block(inter_x.lat, inter_x.lon) 
        FIPS_code = census_json["Block"]["FIPS"]

        neighb = None
        # Create the neighborhood 
        if FIPS_code not in visited_FIPS:
            visited_FIPS.add(FIPS_code)

            neighb = Neighborhood(FIPS_code)
            session.add(neighb)
        else:
            neighb = session.query(Neighborhood).filter(Neighborhood.FIPS_code==FIPS_code).first()

        # Add the current intersection to the neighborhood
        inter_x.neighborhood_id = neighb.id
       
    session.commit()

def get_census_data(session, attr_name, table_code, val_formula):
    header_re = re.compile(CENSUS_HEADER_FORMAT)
    try:
        # (State, Summary Level, State, Table Code)
        request_url = CENSUS_URL % (DC_CODE, TRACT_DETAIL, DC_CODE, table_code)

        census_csv = requests.get(request_url).text
        census_data = [line.split(',') for line in census_csv.split('\n')]
        headers = census_data[0]

        # Do stuff
        new_type = AttributeType(attr_name)
        session.add(new_type)

        # Go from 1 past headers, ignore '' after splitting on 'n'
        for line_idx in xrange(1, len(census_data) - 1):
            line = census_data[line_idx]
            row_val_formula = header_re.sub(partial(map_header, headers=headers, row=line), val_formula)
            val = eval(row_val_formula)

            # Percent for LIKE query
            geo_id = line[0] + '%'
            # Grab the neighborhood based on the FIPS/GEOid code
            # Note that this id is only the first 11 digits...
            neighb = session.query(Neighborhood).\
                    filter(Neighborhood.FIPS_code.like(geo_id)).first()

            # If it's a known neighborhood, add the attribute
            if neighb:
                new_attr = NeighborhoodAttr(val, new_type, neighb.id)
                session.add(new_attr)
        session.commit()
        creation_summary = "Sucessfully created attribute %s from table %s using formula %s." % (attr_name, table_code, val_formula)
        return creation_summary
    except:
        print "An exception occured, refer to the output file for more info"
        #formatted_error = "Error %s" % traceback.format_exception(*sys.exc_info())
        creation_summary = "Unable to create attribute %s from table %s using formula %s.\n Error Code:\n%s" \
                         % (attr_name, table_code, val_formula, traceback.format_exception(*sys.exc_info()))

        return creation_summary
       

def read_tables_from_file(session, in_filename, out_filename):
    '''
    Each line in the file should correlate to a created table.
    Format: <new attribute name>,<table code>,<formula with labels>
    '''
    f = open(in_filename, 'r')
    new_attrs = [line.split(',') for line in f.readlines()]
    f.close()

    with open(out_filename, 'a') as out: 
        for new_attr in new_attrs:
            table_out = get_census_data(session, *new_attrs)
            out.write(table_out)
    

def read_tables_from_terminal(session, out_filename, headers_filename):
    # Grab the header
    header_file = open(headers_filename, 'r')
    master_header_map = json.loads(header_file.read())
    header_file.close()

    with open(out_filename, 'a') as out: 
        create_new = 'y'
        while create_new == 'y':
            table_code = raw_input("From what census table do you want to create the new attribute? ")
            header_key = master_header_map[table_code]
            print "Header Label:" 
            print "-"*80
            pretty_print_json(header_key)
            print "-"*80
            attr_name = raw_input("New attribute name? ")

            # Grab an input formula based on headers
            val_formula = raw_input("Formula (with 'labels' as variables) ")

            confirmation = raw_input("Are you sure? (y/n) ")
            if confirmation == "y":
                print "Creating new attribute"
                table_out = get_census_data(session, attr_name, table_code, val_formula)
                out.write(table_out)
            else:
                print "Aborting attribute creation"
            
            create_new = raw_input("Would you like to create another attribute?(y/n) ")


def map_header(match, headers, row):
    val = row[headers.index(match.group(0))]
    # Handle case when it's either a float or an integer
    return str(float(val))


def pretty_print_json(json_file):
    print json.dumps(json_file, sort_keys=True, indent=4) 
    
def main():
    session = Connector().getDBSession()
    #create_known_neighborhoods(session)
    read_tables_from_terminal(session, 'attr_summary.csv', 'labels.json')

    #census_json = request_census_block(100, 100)
    #pretty_print_json(census_json)


if __name__ == '__main__':
    main()
