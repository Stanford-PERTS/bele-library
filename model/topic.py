"""
Topic Model
===========

Course content topics
"""

import config
import util
import searchable_properties as sndb

from .contentOld import Content


class Topic(Content):

    themes = sndb.StringProperty(repeated=True)  # unordered parents
    lessons = sndb.StringProperty(repeated=True)  # ordered children
    color = sndb.StringProperty(default='#666666')