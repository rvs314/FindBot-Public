from dotenv import load_dotenv
load_dotenv(dotenv_path=".env.local")

import googlemaps
from data import Listing
from functools import lru_cache
import logging

GMAPS_API_KEY = "<YOUR_VERY_OWN_GMAPS_API>"

gmaps = googlemaps.Client(GMAPS_API_KEY)

def includes(geometry, lstng: Listing):
    def between(b1, el, b2):
        if b1 > b2: return between(b2, el, b1)
        return b1 <= el <= b2

    def close(v1, v2, epsilon=0.0001):
        return abs(v1 - v2) < epsilon

    if geometry['location_type'] == 'APPROXIMATE':
        bounds = geometry['bounds']
        ne, sw = bounds['northeast'], bounds['southwest']
        return (between(ne['lat'], lstng.latitude, sw['lat'])
                and between(ne['lng'], lstng.longitude, sw['lng']))
    else:
        loc = geometry['location']
        return (close(loc['lat'], lstng.latitude)
                and close(loc['lng'], lstng.longitude))

@lru_cache
def geocode(loc):
    codes = gmaps.geocode(loc, components = { "locality": "New York City", "country": "US" })
    if len(codes) == 0:
        logging.warning("Attempted to geocode %s, but found no results", loc)
    elif len(codes) > 2:
        logging.warning(f"Attempted to geocode %s, but found {len(codes)} results", loc)

    return codes
