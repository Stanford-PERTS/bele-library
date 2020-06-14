"""Provide example code for writing unit tests."""

from google.appengine.ext import ndb
import unittest

from api import PermissionDenied
from model import (Theme, )
from unit_test_helper import PopulatedTestCase


class PermissionsTest(PopulatedTestCase):
    """Test permissions enforced by the python API (api.py).

    Read more about the kinds of assertions here:
    https://docs.python.org/2/library/unittest.html#unittest.TestCase
    """

    def test_get_by_id(self):
        """Should be open to everyone."""
        # Many of the populated entities are unlisted, so this also
        # demonstrates that getting by id returns unlisted entities.
        for entity in self.populated_entities:
            public_entity = self.public_api.get_by_id(entity.uid)
            normal_entity = self.normal_api.get_by_id(entity.uid)
            admin_entity = self.admin_api.get_by_id(entity.uid)

            self.assertEqual(entity, public_entity)
            self.assertEqual(entity, normal_entity)
            self.assertEqual(entity, admin_entity)

    def test_get_deleted(self):
        """Deleted entities should never be returned."""
        # Create and delete a theme.
        theme = self.admin_api.create('Theme', name="Test Theme", listed=True,
                                      deleted=True)

        # Get the theme by key to enforce consistency.
        theme.key.get()

        # Prove that the deletion worked and is consistent.
        fetched_theme = Theme.query(Theme.name == "Test Theme").get()
        self.assertIsInstance(fetched_theme, Theme)
        self.assertTrue(fetched_theme.deleted)

        # It should no longer appear for anyone, either by id or by query.

        public_entity = self.public_api.get_by_id(theme.uid)
        normal_entity = self.normal_api.get_by_id(theme.uid)
        admin_entity = self.admin_api.get_by_id(theme.uid)

        self.assertIsNone(public_entity)
        self.assertIsNone(normal_entity)
        self.assertIsNone(admin_entity)

        public_results = self.public_api.get('Theme')
        normal_results = self.normal_api.get('Theme')
        admin_results = self.admin_api.get('Theme')

        self.assertNotIn(theme, public_results)
        self.assertNotIn(theme, normal_results)
        self.assertNotIn(theme, admin_results)

    def test_query_listed_and_unlisted(self):
        """Unlisted entities can't be queried, listed ones can."""
        listed_theme = self.admin_api.create('Theme', name="Test Theme",
                                             listed=True)
        unlisted_theme = self.admin_api.create('Theme', name="Test Theme",
                                               listed=False)

        # Get the theme by key to enforce consistency.
        listed_theme.key.get()
        unlisted_theme.key.get()

        public_results = self.public_api.get('Theme')
        normal_results = self.normal_api.get('Theme')
        admin_results = self.admin_api.get('Theme')

        self.assertIn(listed_theme, public_results)
        self.assertIn(listed_theme, normal_results)
        self.assertIn(listed_theme, admin_results)

        self.assertNotIn(unlisted_theme, public_results)
        self.assertNotIn(unlisted_theme, normal_results)

        # Admins CAN see unlisted stuff.
        self.assertIn(unlisted_theme, admin_results)

    def test_owner_queries(self):
        """Users can query unlisted things they own."""

        practice = self.normal_api.create('Practice', name="Test Practice",
                                          listed=False)
        comment = self.normal_api.create('Comment', practice_id=practice.uid,
                                         listed=False)

        # Get the theme by key to enforce consistency.
        practice.key.get()
        comment.key.get()

        results = self.normal_api.get('Practice', ancestor=self.normal_user)
        self.assertIn(practice, results)
        results = self.normal_api.get('Comment', ancestor=self.normal_user)
        self.assertIn(comment, results)

        # But users can't do ancestor queries about anyone but themselves.
        self.assertRaises(PermissionDenied, self.normal_api.get,
                          'Practice', ancestor=self.admin_user)

        # Admins CAN do ancestor queries about others.
        results = self.admin_api.get('Practice', ancestor=self.normal_user)
        self.assertIn(practice, results)
        results = self.admin_api.get('Comment', ancestor=self.normal_user)
        self.assertIn(comment, results)
