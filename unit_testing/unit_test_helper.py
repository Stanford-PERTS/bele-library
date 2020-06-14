"""Making setting up unit tests easier."""

from google.appengine.datastore import datastore_stub_util
from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.ext import testbed
import logging
import unittest

from api import Api
from model import User
import util


class PertsTestCase(unittest.TestCase):
    """Contains important global settings for running unit tests.

    Errors related to logging, and appstats not being able to access memcache,
    would appear without these settings.

    Use Example:

    class MyTestCase(unit_test_help.PertsTestCase):
        def set_up(self):
            # Let PertsTestCase do its important work
            super(MyTestCase, self).setUp()

            # Add your own stubs here
            self.testbed.init_user_stub()

        # Add your tests here
        def test_my_stuff(self):
            pass
    """

    def setUp(self):
        """Sets self.testbed and activates it, among other global settings.

        This function (noticeably not named with PERTS-standard underscore
        case) is automatically called when starting a test by the unittest
        module. We use it for basic configuration and delegate further set
        up to the more canonically named set_up() of inheriting classes.
        """
        if not util.is_localhost():
            # Logging test activity in production causes errors. This
            # suppresses all logs of level critical and lower, which means all
            # of them. See
            # https://docs.python.org/2/library/logging.html#logging.disable
            logging.disable(logging.CRITICAL)

        # Start a clean testing environment for one test.
        self.testbed = testbed.Testbed()
        self.testbed.activate()

        # We have to use a memcache stub so that appstats doesn't complain in
        # production.
        self.testbed.init_memcache_stub()

        # NDB has lots of fancy caching features, whic are normally great, but
        # get in the way of testing consistency.
        # https://cloud.google.com/appengine/docs/python/ndb/cache
        ndb_context = ndb.get_context()
        ndb_context.set_cache_policy(lambda x: False)
        ndb_context.set_memcache_policy(lambda x: False)

        # Let inheriting classes to their own set up.
        if hasattr(self, 'set_up'):
            self.set_up()

    def tearDown(self):
        """Automatically called at end of test by the unittest module."""
        # Re-enable logging.
        logging.disable(logging.NOTSET)
        # Tear down the testing environment used by a single test so the next
        # test gets a fresh start.
        self.testbed.deactivate()


class PopulatedTestCase(PertsTestCase):
    """A standard datastore environment for testing entities.

    Attributes:
        consistency_probability: int, default 0, the probability, as a decimal,
            that an eventually-consistent query will return accurate results
            from recent writes. See: https://cloud.google.com/appengine/docs/python/tools/localunittesting?hl=en#Python_Writing_High_Replication_Datastore_tests

    Defines:
    * self.populated_entities, a tuple
    * self.admin_user
    * self.admin_api
    * self.normal_user
    * self.normal_api
    * self.public_api

    Even if consistency_probability is less than 1, populated entities have
    been forced into a consistent state for convenience by api.populate.
    """

    consistency_probability = 0

    def set_up(self):
        # Create a consistency policy that will simulate the High Replication
        # consistency model. A zero probability means it will be on its 'worst'
        # behavior: eventually consistent queries WILL return stale results.
        self.policy = datastore_stub_util.PseudoRandomHRConsistencyPolicy(
            probability=self.consistency_probability)

        # Initialize the datastore stub with this policy.
        self.testbed.init_datastore_v3_stub(consistency_policy=self.policy)

        # Swap the above two lines with this to see the effects of a more
        # forgiving datastore, where eventually consistent queries MIGHT
        # return stale results.
        # self.testbed.init_datastore_v3_stub()

        # for simulating google users
        self.testbed.init_user_stub()

        # for simulating search
        self.testbed.init_search_stub()

        # Since we have to be able to run these tests from cron, where there's
        # no true sense of a current user making a request, invent an admin
        # to run the populate script.
        self.admin_user = User.create(
            email='',
            auth_id='',
            first_name='Unit', last_name='Testing', is_admin=True)

        # The testing flag allows us to use unsaved user entities to create an
        # api. Normal operation requires that the user be saved to the
        # datastore. This is the only effect; e.g. a testing api still affects
        # the datastore (or, in this case, the test bed datastore).
        self.admin_api = Api(self.admin_user, testing=True)

        self.populated_entities = self.admin_api.populate()

        # Force everything into a consistent state, just in case we're using
        # an inconsistent testbed policy.
        ndb.get_multi([e.key for e in self.populated_entities])

        for e in self.populated_entities:
            if isinstance(e, User) and e.email == '':
                self.normal_user = e
        if not hasattr(self, 'normal_user'):
            raise Exception("PopulatedTestCase could not find normal user.")
        self.normal_api = Api(self.normal_user)

        self.public_api = Api(None)
