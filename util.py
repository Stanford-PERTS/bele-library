"""Collection of utility functions."""

from dateutil import parser as dateutil_parser  # parse_datetime()
from google.appengine.api import app_identity as app_identity
from google.appengine.api import search
from google.appengine.api import users as app_engine_users  # is_god()
from google.appengine.ext import ndb
from google.appengine.ext.ndb import metadata  # delete_everything()
from passlib import hash as passlib_hash  # hash_password
import collections
import copy
import datetime  # parse_date()
import google.appengine.api.app_identity as app_identity  # is_development()
import hashlib
import json  # get_request_dictionary() and hash_dict()
import logging
import os  # is_development(), get_immediate_subdirectories()
import random
import re  # get_request_dictionary() and hash_dict()
import time  # delete_everything()
import unicodedata  # clean_string()
import urllib
import urlparse

import config
from simple_profiler import Profiler

# A 'global' profiler object that's used in BaseHandler.get. So, to profile
# any request handler, add events like this:
# util.profiler.add_event("did the thing")
# and when you're ready, print the results, perhaps like this:
# logging.info(util.profiler)
profiler = Profiler()

# Some poorly-behaved libraries screw with the default logging level,
# killing our 'info' and 'warning' logs. Make sure it's set correctly
# for our code.
logging.getLogger().setLevel(logging.DEBUG)


def clean_string(s):
    """Returns lowercase, ascii-only version of the string. See
    var f for only allowable chars to return."""

    # *Replace* unicode special chars with closest related char, decode to
    # string from unicode.
    if isinstance(s, unicode):
        s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore')
    s = s.lower()
    f = 'abcdefghijklmnopqrstuvwxyz'
    return filter(lambda x: x in f, s)


def delete_everything():
    kinds = metadata.get_kinds()
    for kind in kinds:
        if kind.startswith('_'):
            pass  # Ignore kinds that begin with _, they are internal to GAE
        else:
            q = ndb.Query(kind=kind)
            keys = q.fetch(keys_only=True)

            # Delete 1000 entities at a time.
            for i in range(len(keys) / 1000 + 1):
                portion = keys[i*1000: i*1000+1000]
                ndb.delete_multi(portion)


def delete_all_in_index(index_name):
    """Delete all the docs in the given index.

    Adapted from https://cloud.google.com/appengine/docs/python/search/#Python_Deleting_documents_from_an_index
    """
    index = search.Index(name=index_name)

    # Looping because get_range returns up to 100 documents at a time.
    while True:
        # Get a list of documents populating only the doc_id field and extract
        # the ids.
        document_ids = [document.doc_id
                        for document in index.get_range(ids_only=True)]
        if not document_ids:
            break
        # Delete the documents for the given ids from the index.
        index.delete(document_ids)


def get_immediate_subdirectories(path_string):
    return [name for name in os.listdir(path_string)
            if os.path.isdir(os.path.join(path_string, name))]


def hash_dict(d):
    """Generate a unique, identifying json string from a flat dictionary.
    Use json.loads() to convert back to a dictionary."""
    ordered_d = collections.OrderedDict(sorted(d.items(), key=lambda t: t[0]))
    return json.dumps(ordered_d)


def is_development():
    """Localhost OR the mindsetkit-staging app are development.

    The mindsetkit app is production.
    """
    # see http://stackoverflow.com/questions/5523281/how-do-i-get-the-application-id-at-runtime
    return (is_localhost() or
            app_identity.get_application_id() == 'mindsetkit-staging')


def is_function(x):
    """Actually tests if x is callable, which applies both to user-defined and
    built in (native) python functions.
    See http://stackoverflow.com/questions/624926/how-to-detect-whether-a-python-variable-is-a-function
    """
    return hasattr(x, '__call__')


def is_localhost():
    """Is running on the development SDK, i.e. NOT deployed to app engine."""
    return os.environ['SERVER_SOFTWARE'].startswith('Development')


def list_by(l, p):
    """Turn a list of objects into a dictionary of lists, keyed by p.

    Example: Given list of pd entities and 'user', returns
    {
        'User_ABC': [pd1, pd2],
        'User_DEF': [pd3, pd4],
    }
    Objects lacking property p will be indexed under None.
    """
    d = {}
    for x in l:
        key = getattr(x, p) if hasattr(x, p) else None
        if key not in d:
            d[key] = []
        d[key].append(x)
    return d


def ordinal_suffix(i):
    """Get 'st', 'nd', 'rd' or 'th' as appropriate for an integer."""
    if i < 0:
        raise Exception("Can't handle negative numbers.")

    if i % 100 in [11, 12, 13]:
        return 'th'
    elif i % 10 is 1:
        return 'st'
    elif i % 10 is 2:
        return 'nd'
    elif i % 10 is 3:
        return 'rd'
    else:
        return 'th'


def parse_datetime(s, return_type='datetime'):
    """Takes just about any date/time string and returns a python object.
    Datetime objects are the default, but setting type to 'date' or 'time'
    returns the appropriate object.

    See http://labix.org/python-dateutil
    """

    if return_type not in ['datetime', 'date', 'time']:
        raise Exception("Invalid type: {}.".format(return_type))

    dt = dateutil_parser.parse(s)

    if return_type in ['date', 'time']:
        method = getattr(dt, return_type)
        return method()
    else:
        return dt


def zero_float(string):
    """Try to make a string into a floating point number and make it zero if
    it cannot be cast.  This function is useful because python will throw an
    error if you try to cast a string to a float and it cannot be.
    """
    try:
        return float(string)
    except:
        return 0


def json_dumps_default(obj):
    """Specify this when serializing to JSON to handle more data types.

    Currently can handle dates, times, and datetimes.

    Example:

    json_string = json.dumps(my_object, default=util.json_dumps_default)
    """
    if isinstance(obj, ndb.Key):
        obj = obj.get();
        return obj.uid;
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    else:
        raise TypeError("{} is not JSON serializable. Consider extending "
                        "util.json_dumps_default().".format(obj))


def set_query_parameters(url, new_fragment=None, **new_params):
    """Given a URL, set a query parameter or fragment and return the URL.

    Setting to '' removes the parameter or hash/fragment.

    > set_query_parameter('http://me.com?foo=bar&biz=baz', foo='stuff', biz='')
    'http://me.com?foo=stuff'

    See: http://stackoverflow.com/questions/4293460/how-to-add-custom-parameters-to-an-url-query-string-with-python
    """
    scheme, netloc, path, query_string, fragment = urlparse.urlsplit(url)
    query_params = urlparse.parse_qs(query_string)

    query_params.update(new_params)
    query_params = {k: v for k, v in query_params.items() if v != ''}
    new_query_string = urllib.urlencode(query_params, doseq=True)

    if new_fragment is not None:
        fragment = new_fragment

    return urlparse.urlunsplit(
        (scheme, netloc, path, new_query_string, fragment))


def search_document_to_dict(doc):
    list_properties = [
        'tags',
    ]
    d = {
        'uid': doc.doc_id,
        'rank': int(doc.rank),
    }
    for f in doc.fields:
        if f.name in d:
            # Turn repeated fields into lists
            if type(d[f.name]) is not list:
                d[f.name] = [d[f.name]]
            d[f.name].append(f.value)
        elif f.name in list_properties:
            d[f.name] = [f.value]
        else:
            d[f.name] = f.value
    return d


def get_upload_bucket():
    # The bucket must be created in the app, and it must be set so that all
    # files uploaded to it are public. All of this is easy with the developer's
    # console; look for the three-vertical-dots icon after creating the bucket.

    # Removed line below to get my devserver working, may need to change back for prod
    # return app_identity.get_application_id() + '-upload'

    return app_identity.get_default_gcs_bucket_name()

def extract_value_from_json(value, key):
    if key is None:
        raise Exception('No key parameter supplied')
    if not isinstance(value, basestring):
        raise TypeError
    def assign_vals(_dict, _key):
        if _key in _dict:
            value = _dict[_key]
        else:
            raise Exception('Key: {} does not exist in json'.format(_key))
        return value
    parsed_result = try_parse_json(value, True)
    if parsed_result:
        value = assign_vals(parsed_result, key)
    return value;

def try_parse_json(value, strict=False):
    try:
        value = json.loads(value)
    except ValueError, e:
        if (strict == True):
            value = False
        pass # invalid json, return original input value
    return value;
