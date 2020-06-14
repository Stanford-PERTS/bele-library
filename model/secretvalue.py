"""
SecretValue Model
===========

Class representing an secret key-value pair.
"""


from google.appengine.ext import ndb


class SecretValue(ndb.Model):
    """A secret key-value pair.

    Currently used for storing configuration values, like hash salts.
    """
    value = ndb.StringProperty(default='')
