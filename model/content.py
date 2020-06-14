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
    """Ancestor class for user submitted content.
    """

    tags = sndb.StringProperty(repeated=True, search_type=search.AtomField)
    subjects = sndb.StringProperty(repeated=True, search_type=search.AtomField)
    title = sndb.StringProperty(default='', search_type=search.TextField)
    short_description = sndb.TextProperty(default='', search_type=search.TextField)
    # Added back in for now...
    min_grade = sndb.IntegerProperty(default=0,
                                     search_type=search.NumberField)
    max_grade = sndb.IntegerProperty(default=13,
                                     search_type=search.NumberField)
    # Remove this
    promoted = sndb.BooleanProperty(default=False,
                                    search_type=search.AtomField)
    # User that last modified the content
    last_edited_by = sndb.StringProperty(default='')
