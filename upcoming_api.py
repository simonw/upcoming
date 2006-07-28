"""
A simple Python module for accessing the Upcoming API.

Example usage:

>>> from upcoming_api import Upcoming
>>> upcoming = Upcoming(YOUR_UPCOMING_API_KEY)
>>> flickr_events = upcoming.search(search_text='flickr')
>>> len(flickr_events)
39
>>> from pprint import pprint
>>> pprint(flickr_events[1])
{'category_id': 4,
 'date_posted': datetime.datetime(2006, 7, 14, 9, 58, 25),
 'description': 'All are welcome.  Bring your toys.  We&#39;ll be on the patio.',
 'end_date': None,
 'end_time': None,
 'id': 91569,
 'metro_id': '13',
 'name': 'Toronto Flickr Meetup',
 'personal': True,
 'selfpromotion': False,
 'start_date': datetime.date(2006, 7, 27),
 'start_time': datetime.time(19, 0),
 'user_id': 11021,
 'venue_id': 28279}
>>> pprint(upcoming.venue.getInfo(flickr_events[1]['venue_id']))
[{'address': '1296 Queen Street West',
  'city': 'Toronto',
  'description': '',
  'id': 28279,
  'name': 'Cadillac Lounge',
  'phone': '',
  'private': False,
  'url': '',
  'user_id': 63312,
  'zip': ''}]

If you're making a lot of calls to methods such as venue.getInfo which don't
change very often, it's worth using the UpcomingCached class:

>>> from upcoming_api import UpcomingCached
>>> upcoming = UpcomingCached(YOUR_UPCOMING_API_KEY)
>>> venue = upcoming.venue.getInfo(28729) # Makes an HTTP request
>>> venue = upcoming.venue.getInfo(28729) # No request; uses cached information

The cache currently uses an in-memory store; you can customise its behaviour
by creating your own class matching the interface of the SimpleCache class
and passing an instance of it as the second argument to the UpcomingCached
constructor.

"""

import datetime, sys, urllib, re
from xml.dom import minidom

UPCOMING_API = "http://upcoming.org/services/rest/"

try:
    set
except NameError:
    from sets import Set as set

# Attribute conversion functions
string = lambda s: s.encode('utf8')
tag_str = lambda s: s.split(',')

def date(s):
    # 2006-06-08 12:00:36
    bits = re.match(
        r'^(\d{4})-(\d{2})-(\d{2}) ?(\d{2})?:?(\d{2})?:?(\d{2})?', s
    ).groups()
    bits = [bit for bit in bits if bit is not None]
    if len(bits) == 3:
        return datetime.date(*map(int, bits))
    else:
        return datetime.datetime(*map(int, bits))

def date_or_null(s):
    if s and not s.startswith('0000-'):
        return date(s)
    return None

def time_or_null(s):
    if s:
        return datetime.time(*map(int, s.split(':')))
    else:
        return None

boolean = lambda s: bool(int(s))

# Returned elements and attribute conversion rules
TOKEN = 'token', {
    'token': string,
    'user_id': int,
    'user_name': string,
    'user_username': string,
}
EVENT = 'event', {
    'id': int,
    'name': string,
    'tags': tag_str,
    'description': string,
    'start_date': date,
    'end_date': date_or_null,
    'start_time': time_or_null,
    'end_time': time_or_null,
    'personal': boolean,
    'selfpromotion': boolean,
    'metro_id': string,
    'venue_id': int,
    'user_id': int,
    'category_id': int,
    'date_posted': date
}
EVENT_SEARCH_RESULT = 'event', { # Same as above but no tags
    'id': int,
    'name': string,
    'description': string,
    'start_date': date,
    'end_date': date_or_null,
    'start_time': time_or_null,
    'end_time': time_or_null,
    'personal': boolean,
    'selfpromotion': boolean,
    'metro_id': string,
    'venue_id': int,
    'user_id': int,
    'category_id': int,
    'date_posted': date
}
WATCHLIST_USER = 'user', {
    'id': int,
    'name': string,
    'username': string,
    'status': string
}
METRO = 'metro', {
    'id': int,
    'name': string,
    'code': string,
    'state_id': int
}
METRO_EXTENDED = 'metro', {
    'id': int,
    'name': string,
    'code': string,
    'state_code': string,
    'country_code': string,
    'url': string,
    'state_id': int
}
METRO_SHORT = 'metro', {
    'id': int,
    'name': string,
    'code': string
}
STATE = 'state', {
    'id': int,
    'name': string,
    'code': string
}
COUNTRY = 'country', {
    'id': int,
    'name': string,
    'code': string
}
VENUE = 'venue', {
    'id': int,
    'name': string,
    'address': string,
    'city': string,
    'zip': string,
    'phone': string,
    'url': string,
    'description': string,
    'user_id': int,
    'private': boolean
}
VENUE_SHORT = 'venue', {
    'id': int,
    'name': string,
    'city': string,
    'url': string,
    'user_id': int,
    'private': boolean
}
VENUE_SEARCH_RESULT = 'venue', {
    'id': int,
    'name': string,
    'address': string,
    'city': string,
    'state': string,
    'zip': string,
    'country': string,
    'url': string,
    'description': string,
    'user_id': int,
    'private': boolean
}
CATEGORY = 'category', {
    'id': int,
    'name': string,
    'description': string
}
WATCHLIST = 'watchlist', {
    'id': int,
    'event_id': int,
    'status': string
}
USER = 'user', {
    'id': int,
    'name': string,
    'username': string,
    'zip': string,
    'photourl': string,
    'url': string
}
WATCHLIST_EVENT = 'event', {
    'username': string,
    'status': string,
    'id': int,
    'name': string,
    'tags': tag_str,
    'description': string,
    'start_date': date,
    'end_date': date_or_null,
    'start_time': time_or_null,
    'end_time': time_or_null,
    'personal': boolean,
    'metro_id': string,
    'venue_id': int,
    'user_id': int,
    'category_id': int,
}
UPCOMING_METHODS = {
    # auth
    'auth.getToken': {
        'http_method': 'GET',
        'required': ['frob'],
        'optional': [],
        'returns': TOKEN
    },
    'auth.checkToken': {
        'http_method': 'GET',
        'required': ['token'],
        'optional': [],
        'returns': TOKEN
    },
    # event
    'event.getInfo': {
        'http_method': 'GET',
        'required': ['event_id'],
        'optional': ['token'],
        'returns': EVENT,
        'cachable': True
    },
    'event.add': {
        'http_method': 'POST',
        'required': ['token', 'name', 'venue_id', 'category_id', 'start_date'],
        'optional': ['end_date', 'start_time', 'end_time', 'description', 
            'personal', 'selfpromotion'],
        'returns': EVENT
    },
    'event.search': {
        'http_method': 'GET',
        'required': [],
        'optional': ['search_text', 'country_id', 'state_id', 'metro_id',
            'venue_id', 'min_date', 'max_date', 'tags', 'per_page', 'page',
            'sort', 'token'],
        'returns': EVENT_SEARCH_RESULT
    },
    'event.getWatchlist': {
        'http_method': 'GET',
        'required': ['token', 'event_id'],
        'optional': [],
        'returns': WATCHLIST_USER
    },
    # metro
    'metro.getInfo': {
        'http_method': 'GET',
        'required': ['metro_id'],
        'optional': [],
        'returns': METRO,
        'cachable': True
    },
    'metro.search': {
        'http_method': 'GET',
        'required': [],
        'optional': ['search_text', 'country_id', 'state_id'],
        'returns': METRO_EXTENDED
    },
    'metro.getMyList': {
        'http_method': 'GET',
        'required': ['token'],
        'optional': [],
        'returns': METRO_SHORT
    },
    'metro.getList': {
        'http_method': 'GET',
        'required': ['state_id'],
        'optional': [],
        'returns': METRO_SHORT,
        'cachable': True
    },
    'metro.getStateList': {
        'http_method': 'GET',
        'required': ['country_id'],
        'optional': [],
        'returns': STATE,
        'cachable': True
    },
    'metro.getCountryList': {
        'http_method': 'GET',
        'required': [],
        'optional': [],
        'returns': COUNTRY,
        'cachable': True
    },
    # venue
    'venue.add': {
        'http_method': 'POST',
        'required': ['token', 'venuename', 'venueaddress', 'venuecity',
            'metro_id'],
        'optional': ['venuezip', 'venuephone', 'venueurl', 'venuedescription',
            'private'],
        'returns': VENUE
    },
    'venue.getInfo': {
        'http_method': 'GET',
        'required': ['venue_id'],
        'optional': ['token'],
        'returns': VENUE,
        'cachable': True
    },
    'venue.getList': {
        'http_method': 'GET',
        'required': ['metro_id'],
        'optional': ['token'],
        'returns': VENUE_SHORT
    },
    'venue.search': {
        'http_method': 'GET',
        'required': [],
        'optional': ['search_text', 'country_id', 'state_id', 'metro_id',
            'token'],
        'returns': VENUE_SEARCH_RESULT
    },
    # category
    'category.getList': {
        'http_method': 'GET',
        'required': [],
        'optional': [],
        'returns': CATEGORY,
        'cachable': True
    },
    # watchlist
    'watchlist.getList': {
        'http_method': 'GET',
        'required': ['token'],
        'optional': ['min_date', 'max_date', 'sort'],
        'returns': WATCHLIST
    },
    'watchlist.add': {
        'http_method': 'POST',
        'required': ['token', 'event_id'],
        'optional': ['status'],
        'returns': ('watchlist', {
            'id': int
        })
    },
    'watchlist.remove': {
        'http_method': 'POST',
        'required': ['token', 'watchlist_id'],
        'optional': [],
        'returns': None
    },
    # user
    'user.getInfo': {
        'http_method': 'GET',
        'required': ['user_id'],
        'optional': [],
        'returns': USER,
        'cachable': True
    },
    'user.getInfoByUsername': {
        'http_method': 'GET',
        'required': ['username'],
        'optional': [],
        'returns': USER,
        'cachable': True
    },
    'user.getMetroList': {
        'http_method': 'GET',
        'required': ['token'],
        'optional': [],
        'returns': METRO
    },
    'user.getWatchlist': {
        'http_method': 'GET',
        'required': ['token', 'user_id'],
        'optional': [],
        'returns': WATCHLIST_EVENT
    }
}

class UpcomingError(Exception):
    pass

class UpcomingAccumulator:
    def __init__(self, upcoming_obj, name):
        self.upcoming_obj = upcoming_obj
        self.name = name
    def __getattr__(self, attr):
        return UpcomingAccumulator(self.upcoming_obj, self.name + '.' + attr)
    def __repr__(self):
        return self.name
    def __call__(self, *args, **kw):
        return self.upcoming_obj.callMethod(self.name, *args, **kw)

class Upcoming:
    def __init__(self, api_key):
        self.api_key = api_key
        for method, _ in UPCOMING_METHODS.items():
            category = method.split('.')[0]
            if not hasattr(self, category):
                setattr(self, category, UpcomingAccumulator(self, category))

    def callMethod(self, method, *args, **kw):
        kw['api_key'] = self.api_key
        kw['method'] = method
        try:
            meta = UPCOMING_METHODS[method]
        except KeyError:
            raise UpcomingError, "Invalid method specified"
        if args:
            # Positional arguments are treated in order of method description
            names = meta['required'] + meta['optional']
            for i in range(len(args)):
                kw[names[i]] = args[i]
        # Check we have all required arguments
        required = meta['required'] + ['api_key']
        if len(set(required) - set(kw.keys())) > 0:
            raise UpcomingError, "Required arguments for %s: %s" % \
                (method, ', '.join(meta['required']))
        # Retrieve and parse in to DOM
        qs = urllib.urlencode(kw.items())
        try:
            if meta['http_method'] == 'GET':
                u = urllib.urlopen(UPCOMING_API + '?' + qs)
            else:
                u = urllib.urlopen(UPCOMING_API, qs)
        except: # TODO: Naked excepts are always bad. Make explicit
            raise UpcomingError, "HTTP error: %s, %s: %s" % \
                (UPCOMING_API, qs, sys.exc_info()[0])
        try:
            dom = minidom.parse(u)
        except: # TODO: Another one!
            raise UpcomingError, "Service returned invalid XML: %s" % \
                sys.exc_info()[0]
        # Spot upcoming errors
        if dom.firstChild.getAttribute('stat') != 'ok':
            errors = dom.getElementsByTagName('error')
            if errors:
                msg = errors[0].getAttribute('msg')
            else:
                msg = 'Status not OK'
            raise UpcomingError, msg
        if not meta['returns']:
            return True # Method returns nothing, but finished fine
        # Return a list of dictionaries using type conversions in meta
        results = []
        element, conversions = meta['returns']
        for node in dom.getElementsByTagName(element):
            d = {}
            for key, conversion in conversions.items():
                d[key] = conversion(node.getAttribute(key))
            results.append(d)
        return results



# Optional caching layer; caches calls to cachable methods in a cache object, 
# which is any object with get and put methods that can stash away a simple
# Python data structure. This should help keep the venue.getInfo() etc calls
# down to a minimum.

class UpcomingCached(Upcoming):
    def __init__(self, api_key, cache = None):
        self.cache = cache or SimpleCache()
        Upcoming.__init__(self, api_key)

    def callMethod(self, method, *args, **kw):
        if self.cachable(method):
            # Try the cache stuff
            key = self.makeKey(*([method] + list(args)), **kw)
            hit = self.cache.get(key)
            if hit:
                return hit
            else:
                data = Upcoming.callMethod(self, method, *args, **kw)
                self.cache.set(key, data)
                return data
        # Wasn't cachable; run as normal
        return Upcoming.callMethod(self, method, *args, **kw)

    def cachable(self, method):
        try:
            UPCOMING_METHODS[method]['cachable']
        except KeyError:
            return False
        return True

    def makeKey(self, *args, **kw):
        args = map(str, args)
        args.sort()
        s = ''.join(args)
        keys = kw.keys()
        keys.sort()
        s += ''.join(['%s%s' % (key, kw[key]) for key in keys])
        return s

class SimpleCache:
    def __init__(self):
        self.store = {}
    def get(self, key):
        return self.store.get(key, None)
    def set(self, key, obj):
        self.store[key] = obj

