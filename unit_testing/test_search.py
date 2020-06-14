"""Unit tests related to indexed searching."""

from google.appengine.api import search
import unittest

from cron import Cron
from model import (Model, Indexer, User, Lesson, Practice)
from unit_test_helper import PopulatedTestCase
import config
import util


class ConsistentSearchTest(PopulatedTestCase):
    """Test search indexing."""

    def set_up(self):
        """Overrides PopulatedTestCase.set_up() to change consistency."""
        # This test suite IGNORES datastore inconsistency because it is only
        # interested in what content eventually gets into the search index.
        #
        # Consequently, this suite should only contain tests where this
        # assumption is both valid and required. Any other test should use the
        # default PopulatedTest Case, which assumes maximum inconsistency.
        self.consistency_probability = 1
        super(ConsistentSearchTest, self).set_up()

        # We'll want ready access to a Cron instance and the content search
        # index.
        self.cron = Cron(self.admin_api)
        indexer = Indexer.get_or_insert('the-indexer')
        indexer.delete_all_content()  # fresh start, no pre-populated stuff
        self.search_index = indexer.get_index()

    def test_index_excludes_users(self):
        """Users are both 1) a kind that should never be indexed and 2) a
        placeholder for all kinds that aren't in config.indexed_models."""
        self.admin_api.create(
            'User', email='',
            auth_id='',
            last_name='Doe', first_name='John')
        self.cron.index()
        result_dicts = [util.search_document_to_dict(doc)
                        for doc in self.search_index.get_range()]
        result_kinds = [Model.get_kind(d['uid']) for d in result_dicts]
        self.assertNotIn('User', result_kinds)

    def test_index_excludes_unlisted(self):
        """Content which is normally searchable is not if unlisted."""
        self.admin_api.create(
            'Lesson',
            id='unindexed-lesson',
            name=u'Unindexed Lesson',
            summary=u"R\xf8ckin'",
            tags=['tagone', 'tagtwo'],
            min_grade=5,
            max_grade=8,
            subjects=['reading', 'writing'],
            json_properties={'a': u'\xeb', 'b': [1, 2, 3]},
            listed=False,
        )

        result_dicts = [util.search_document_to_dict(doc)
                        for doc in self.search_index.get_range()]
        result_kinds = [Model.get_kind(d['uid']) for d in result_dicts]
        self.assertNotIn('Lesson', result_kinds)

    def test_index_includes_lesson(self):
        """Lessons should be searchable after creation via put hook."""
        self.admin_api.create(
            'Lesson',
            id='indexed-lesson',
            name=u'Indexed Lesson',
            summary=u"R\xf8ckin'",
            tags=['tagone', 'tagtwo'],
            min_grade=5,
            max_grade=8,
            subjects=['reading', 'writing'],
            json_properties={'a': u'\xeb', 'b': [1, 2, 3]},
            listed=True,
        )

        result_dicts = [util.search_document_to_dict(doc)
                        for doc in self.search_index.get_range()]
        result_kinds = [Model.get_kind(d['uid']) for d in result_dicts]
        self.assertIn('Lesson', result_kinds)

    def test_index_includes_practice(self):
        """Practices should be searchable after creation via put hook."""
        self.normal_api.create(
            'Practice',
            name=u'Indexed Practice',
            summary=u"R\xf8ckin'",
            tags=['super', u'c\xf8\xf8l', 'tagone'],
            subjects=['math', 'history', 'reading'],
            min_grade=0,
            max_grade=13,
            type='text',
            body=u"R\xf8ckin'",
            youtube_id='https://www.youtube.com/watch?v=6sJqTDaOrTg',
            has_files=True,
            pending=False,
            listed=True,
        )

        result_dicts = [util.search_document_to_dict(doc)
                        for doc in self.search_index.get_range()]
        result_kinds = [Model.get_kind(d['uid']) for d in result_dicts]
        self.assertIn('Practice', result_kinds)
