"""
Content Model
===========

Ancestor class for searchable content objects;
Themes, Topics, Lessons, Practices
"""

from google.appengine.api import search
import string

import config
import util
import searchable_properties as sndb

from .model import Model


class Content(Model):
    """Ancestor class for curated content objects: Theme, Topic, Lesson, and
    Practice.
    """

    name = sndb.StringProperty(required=True, search_type=search.TextField)
    summary = sndb.TextProperty(default='', search_type=search.TextField)
    tags = sndb.StringProperty(repeated=True, search_type=search.AtomField)
    subjects = sndb.StringProperty(repeated=True, search_type=search.AtomField)
    min_grade = sndb.IntegerProperty(default=0,
                                     search_type=search.NumberField)
    max_grade = sndb.IntegerProperty(default=13,
                                     search_type=search.NumberField)
    promoted = sndb.BooleanProperty(default=False,
                                    search_type=search.AtomField)
