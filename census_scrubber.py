import requests
import json
from data_model import Intersection
from utility import Connector

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
    for inter_x in intersections:
        census_json = request_census_block(inter_x.lat, inter_x.lon) 
        FIPS_code = census_json["Block"]["FIPS"]


def get_census_tables(FIPS_code):
    # Isolate the first two characters from 15 digit FIPS code
    state_code = FIPS_code / 10**13
    
    # (State, Summary Level, State, Table Code)
    request_url = CENSUS_URL % (state_code, TRACT_DETAIL, state_code, CENSUS_TABLES[0])

    census_csv = requests.get(request_url).text
    # Remove SUMLEV, STATE, COUNTY
    with open('test.csv', 'w') as f:
        f.write(census_csv.text)



def categorize_intersections(session):
    pass

def pretty_print_json(json_file):
    print json.dumps(json_file, sort_keys=True, indent=4) 
    


def main():
    session = Connector().getDBSession()
    #create_known_neighborhoods(session)
    get_census_tables(510131034022000)

    #census_json = request_census_block(100, 100)
    #pretty_print_json(census_json)


if __name__ == '__main__':
    main()
