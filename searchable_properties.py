"""Simple extensions of ndb model properties with search-related metadata."""


from google.appengine.ext import ndb

class BooleanProperty(ndb.BooleanProperty):
    def __init__(self, *args, **kwargs):
        self.search_type = kwargs.pop('search_type', None)
        super(BooleanProperty, self).__init__(*args, **kwargs)


class ComputedProperty(ndb.ComputedProperty):
    def __init__(self, *args, **kwargs):
        self.search_type = kwargs.pop('search_type', None)
        super(ComputedProperty, self).__init__(*args, **kwargs)


class DateProperty(ndb.DateProperty):
    def __init__(self, *args, **kwargs):
        self.search_type = kwargs.pop('search_type', None)
        super(DateProperty, self).__init__(*args, **kwargs)


class DateTimeProperty(ndb.DateTimeProperty):
    def __init__(self, *args, **kwargs):
        self.search_type = kwargs.pop('search_type', None)
        super(DateTimeProperty, self).__init__(*args, **kwargs)


class IntegerProperty(ndb.IntegerProperty):
    def __init__(self, *args, **kwargs):
        self.search_type = kwargs.pop('search_type', None)
        super(IntegerProperty, self).__init__(*args, **kwargs)


class StringProperty(ndb.StringProperty):
    def __init__(self, *args, **kwargs):
        self.search_type = kwargs.pop('search_type', None)
        super(StringProperty, self).__init__(*args, **kwargs)


class TextProperty(ndb.TextProperty):
    def __init__(self, *args, **kwargs):
        self.search_type = kwargs.pop('search_type', None)
        super(TextProperty, self).__init__(*args, **kwargs)

class KeyProperty(ndb.KeyProperty):
    def __init__(self, *args, **kwargs):
        self.search_type = kwargs.pop('search_type', None)
        super(KeyProperty, self).__init__(*args, **kwargs)

class StructuredProperty(ndb.StructuredProperty):
    def __init__(self, *args, **kwargs):
        self.search_type = kwargs.pop('search_type', None)
        super(StructuredProperty, self).__init__(*args, **kwargs)
