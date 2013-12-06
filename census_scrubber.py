import requests
import json
import re
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

# Ignoring if lat/long on a border
API_URL = 'http://data.fcc.gov/api/block/%i/find?format=%s&latitude=%s&longitude=%s&showall=false'
JSON = 'json'
XML = 'xml'


# (State, Summary Level, State, Table Code)
CENSUS_URL = 'http://censusdata.ire.org/%i/all_%i_in_%i.%s.csv'

# Just various codes from http://census.ire.org/data/bulkdata.html
DC_CODE = 11
TRACT_DETAIL = 140
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

def get_census_data(session, headers_filename, FIPS_code):

    
    # Grab the header
    header_file = open(headers_filename, 'r')
    master_header_map = json.loads(header_file.read())
    header_file.close()

    # Isolate the first two characters from 15 digit FIPS code
    state_code = FIPS_code / 10**13
    
    for table_code in CENSUS_TABLES:
        # (State, Summary Level, State, Table Code)
        request_url = CENSUS_URL % (state_code, TRACT_DETAIL, state_code, table_code)

        census_csv = requests.get(request_url).text
        census_data = [line.split(',') for line in census_csv.split('\n')]
        headers = census_data[0]

        header_key = master_header_map[table_code]
        print "Header Label:" 
        print "-"*80
        pretty_print_json(header_key)
        print "-"*80
        attr_name = raw_input("New attribute name? ")

        # Grab an input formula based on headers
        val_formula = raw_input("Formula (with 'labels' as variables) ")
        variables = re.findall(r'[A-Z]\d+', val_formula)
        #variable_indices = [headers.index(var) for var in variables]

        confirmation = raw_input("Are you sure? (yes/no) ")
        if confirmation == 'yes':
            # Do stuff
            new_type = AttributeType(attr_name)
            session.add(new_type)

            # Go from 1 past headers, ignore '' after splitting on 'n'
            for line_idx in xrange(1, len(census_data) - 1):
                line = census_data[line_idx]
                row_val_formula = re.sub(r'[A-Z]\d+', partial(map_header, headers=headers, row=line), val_formula)
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
       

def map_header(match, headers, row):
    val = row[headers.index(match.group(0))]
    # Handle case when it's either a float or an integer
    return str(float(val))


def pretty_print_json(json_file):
    print json.dumps(json_file, sort_keys=True, indent=4) 
    
def main():
    session = Connector().getDBSession()
    #create_known_neighborhoods(session)
    get_census_data(session, 'labels.json', 110131034022000)

    #census_json = request_census_block(100, 100)
    #pretty_print_json(census_json)


if __name__ == '__main__':
    main()
