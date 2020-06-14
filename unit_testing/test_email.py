"""Unit tests related to the Email model"""

from google.appengine.ext import ndb
import unittest
import os

from api import Api, PermissionDenied
from model import (Comment, Email)
from unit_test_helper import PopulatedTestCase


class ConsistentEmailTest(PopulatedTestCase):
    """Test emailing functionality for Email model (email.py)

    Read more about the kinds of assertions here:
    https://docs.python.org/2/library/unittest.html#unittest.TestCase
    """

    def set_up(self):
        """Overrides PopulatedTestCase.set_up() to change consistency."""
        # This test suite IGNORES datastore inconsistency because it is only
        # interested in which emails _eventually_ get sent, not whether a given
        # query is accurate at any given moment.
        #
        # Consequently, this suite should only contain tests where this
        # assumption is both valid and required. Any other test should use the
        # default PopulatedTest Case, which assumes maximum inconsistency.
        self.consistency_probability = 1
        super(ConsistentEmailTest, self).set_up()

    def test_comment_creates_email(self):
        # Create a comment on a new practice
        practice = self.normal_api.create('Practice',
                                          name=u'Spam Checker',
                                          summary=u"This is a summary for the practice",
                                          body=u"This is the body of the practice",
                                          pending=False,
                                          listed=True,
                                          )
        commenter = self.admin_api.create('User',
                                          email='unit_testing+',
                                          auth_id='own:unit_testing+',
                                          first_name='Commenting',
                                          last_name='User',
                                          )
        commenter_api = Api(commenter)
        comment = commenter_api.create('Comment',
                                       body='Wow, what a great practice.',
                                       practice_id=practice.uid,
                                       )
        fetched_email = Email.query().get()
        # The email is about the posted comment...
        self.assertEqual(fetched_email.template_data['comment_body'], comment.body)
        # ...and is going to the owner of the practice.
        self.assertEqual(fetched_email.to_address, self.normal_user.email)

    def test_spam_with_single_email(self):
        # Create a single email
        to_address = ''
        email = self.admin_api.create('Email', to_address=to_address)
        Email.send_pending_email()

        fetched_email = Email.query(Email.to_address == to_address).get()
        self.assertIsInstance(fetched_email, Email)
        # Test if email was attempted to send
        self.assertEqual(fetched_email.was_attempted, True)
        # ...and has been sent
        self.assertEqual(fetched_email.was_sent, True)

    def test_spam_with_two_emails_to_same_address(self):
        # Create a single email
        to_address = ''
        email = self.admin_api.create('Email', to_address=to_address)
        second_email = self.admin_api.create('Email', to_address=to_address)
        Email.send_pending_email()

        fetched_email = Email.query().fetch()
        self.assertEqual(len(fetched_email), 2)
        self.assertIsInstance(fetched_email[0], Email)
        self.assertIsInstance(fetched_email[1], Email)
        # Test if email was attempted to send
        self.assertEqual(fetched_email[0].was_attempted, True)
        self.assertEqual(fetched_email[1].was_attempted, True)
        # ...and has been sent
        self.assertEqual(fetched_email[0].was_sent, True)
        self.assertEqual(fetched_email[1].was_sent, False)

    def test_spam_with_two_emails_to_different_addresses(self):
        # Create a single email
        to_address = ''
        second_address = ''
        email = self.admin_api.create('Email', to_address=to_address)
        second_email = self.admin_api.create('Email', to_address=second_address)
        Email.send_pending_email()

        fetched_email = Email.query().fetch()
        self.assertEqual(len(fetched_email), 2)
        self.assertIsInstance(fetched_email[0], Email)
        self.assertIsInstance(fetched_email[1], Email)
        # Test if email was attempted to send
        self.assertEqual(fetched_email[0].was_attempted, True)
        self.assertEqual(fetched_email[1].was_attempted, True)
        # ...and has been sent
        self.assertEqual(fetched_email[0].was_sent, True)
        self.assertEqual(fetched_email[1].was_sent, True)

    def test_spam_with_recent_email_to_same_addresses(self):
        # Create a sent and not sent email to same address
        # Note: Cannot be to a '@mindsetkit.org' address
        to_address = ''
        email_subject = 'Email subject'
        sent_email = self.admin_api.create(
            'Email', to_address=to_address,
            was_attempted=True,
            was_sent=True)
        email = self.admin_api.create(
            'Email', to_address=to_address,
            subject=email_subject)
        Email.send_pending_email()

        fetched_email = Email.query(Email.subject == email_subject).get()
        self.assertIsInstance(fetched_email, Email)
        # Test if email was attempted to send
        self.assertEqual(fetched_email.was_attempted, True)
        # ...and has been sent
        self.assertEqual(fetched_email.was_sent, False)

    def test_spam_with_recent_email_to_different_addresses(self):
        # Create a sent and not sent email to different addresses
        # Note: Cannot be to a '@mindsetkit.org' address
        to_address = ''
        second_address = ''
        email_subject = 'Email subject'
        sent_email = self.admin_api.create(
            'Email', to_address=to_address,
            was_attempted=True,
            was_sent=True,)
        email = self.admin_api.create(
            'Email', to_address=second_address,
            subject=email_subject)
        Email.send_pending_email()

        fetched_email = Email.query(Email.subject == email_subject).get()
        self.assertIsInstance(fetched_email, Email)
        # Test if email was attempted to send
        self.assertEqual(fetched_email.was_attempted, True)
        # ...and has been sent
        self.assertEqual(fetched_email.was_sent, True)
