"""
Lesson Model
===========

Course content lessons (searchable)
"""

from google.appengine.api import search

import config
import util
import searchable_properties as sndb

from .contentOld import Content


class Lesson(Content):

    topics = sndb.StringProperty(repeated=True)  # unordered parents
    popular_in = sndb.StringProperty(repeated=True)  # unordered parents
    type = sndb.StringProperty(default='text', search_type=search.AtomField)
    youtube_id = sndb.StringProperty(default='')
    wistia_id = sndb.StringProperty(default='')
    votes_for = sndb.IntegerProperty(default=0, search_type=search.NumberField)
    num_comments = sndb.IntegerProperty(default=0,
                                        search_type=search.NumberField)

    def to_search_document(self, rank=None):
        """Extends inherited method in Model."""
        fields = super(Lesson, self)._get_search_fields()

        # Simplify checking for video
        if self.type == 'video':
            fields.append(search.AtomField(name='content_type', value='video'))

        return search.Document(doc_id=self.uid, fields=fields, rank=rank,
                               language='en')