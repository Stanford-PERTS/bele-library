"""Chris wrote this file to firm up how api.get is handled. This became less
important once we started using indexed search. The code to pass the unit tests
below was never written, but these are here for reference in case it becomes
important again."""

# """Test our Api, defined in api.py."""

# from google.appengine.ext import ndb
# import math
# import unittest

# from api import PermissionDenied
# from model import (Theme, )
# from unit_test_helper import PopulatedInconsistentTestCase


# class ApiTest(PopulatedInconsistentTestCase):
#     """Test our Api (api.py).

#     Read more about the kinds of assertions here:
#     https://docs.python.org/2/library/unittest.html#unittest.TestCase
#     """

#     def test_get_with_default_n(self):
#         # This is now many we can expect (by using ndb directly).
#         num_results = Theme.query(
#             Theme.listed == True, Theme.deleted == False).count()

#         public_results = self.public_api.get('Theme')
#         normal_results = self.normal_api.get('Theme')
#         admin_results = self.admin_api.get('Theme')

#         self.assertEqual(len(public_results), num_results)
#         self.assertEqual(len(normal_results), num_results)
#         self.assertEqual(len(admin_results), num_results)

#     def test_get_with_integer_n(self):
#         # Excluding public, b/c it's not allowed to set n.
#         normal_results = self.normal_api.get('Theme', n=1)
#         admin_results = self.admin_api.get('Theme', n=1)

#         self.assertEqual(len(normal_results), 1)
#         self.assertEqual(len(admin_results), 1)

#     def test_get_with_infinite_n(self):
#         # This is now many we can expect (by using ndb directly).
#         num_results = Theme.query(
#             Theme.listed == True, Theme.deleted == False).count()

#         infinity = float('inf')

#         # Excluding public, b/c it's not allowed to set n.
#         normal_results = self.normal_api.get('Theme', n=infinity)
#         admin_results = self.admin_api.get('Theme', n=infinity)

#         # "Infinite" result sets are really just iterators, and the only way
#         # to get the length of an iterator is to iterate it.
#         self.assertEqual(len([e for e in normal_results]), num_results)
#         self.assertEqual(len([e for e in admin_results]), num_results)

#     def test_limit_subqueries_with_default_n(self):
#         """Complex filters overload the datastore; our api can intervene."""
#         # These two combined create 10 * 4 = 40 subqueries, too many for the
#         # datastore, triggering our limit_subqueries and post_process logic.
#         long_filter_1 = ['one', 'two', 'three', 'four', 'five', 'size',
#                          'seven', 'eight', 'nine', 'ten']
#         long_filter_2 = ['reading', 'writing', 'arithmetic', 'raging']
