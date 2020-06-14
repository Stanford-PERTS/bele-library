"""
Indexer Model
===========

Model for searchable content indexer
"""

from google.appengine.api import search
from google.appengine.ext import ndb
import datetime
import logging

import config
import util

from .lesson import Lesson
from .model import Model
from .practice import Practice


class Indexer(ndb.Model):
    """Update content search index with recently modified entities.

    orginal author
    bmh September 2013
    """

    # Data
    last_check = ndb.DateTimeProperty()
    # Limit the number of items we are willing to index
    max_entities_to_index = 10

    def get_index(self):
        return search.Index(name=config.content_index)

    def get_all_content_classes(self):
        kinds = [k for k in ndb.metadata.get_kinds()
                 if k in config.indexed_models]
        return [Model.get_class(k) for k in kinds]

    def get_all_content_entities(self):
        Klasses = self.get_all_content_classes()

        entities = [
            e for klass in Klasses
            for e in (klass.query(getattr(klass, 'listed') == True)
                      .order(getattr(klass, 'modified')))
        ]

        return entities

    def get_changed_content_entities(self):
        Klasses = self.get_all_content_classes()

        # If the last check timestamp isn't set, set it to the earliest
        # possible time, forcing it to start over and index all content
        # regardless of its age.
        if not self.last_check:
            self.last_check = datetime.datetime(1, 1, 1)

        entities = [
            e for klass in Klasses
            for e in (klass.query(getattr(klass, 'modified') > self.last_check)
                      .order(getattr(klass, 'modified'))
                      .filter(getattr(klass, 'listed') == True)
                      .fetch(self.max_entities_to_index))
        ]

        return entities

    def delete_all_content(self):
        """Deletes all the documents in the content index.

        https://cloud.google.com/appengine/docs/python/search/#Python_Deleting_documents_from_an_index
        """
        index = self.get_index()

        # Looping because get_range by default returns up to 100 documents at a
        # time.
        num_deleted = 0
        while True:
            # Get a list of documents populating only the doc_id field and
            # extract the ids.
            document_ids = [document.doc_id
                            for document in index.get_range(ids_only=True)]
            if not document_ids:
                break
            # Delete the documents for the given ids from the Index.
            index.delete(document_ids)
            num_deleted += len(document_ids)

        return num_deleted