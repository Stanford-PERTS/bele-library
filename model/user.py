"""
User Model
===========
"""

from google.appengine.api import images
from google.appengine.api import search
from google.appengine.ext import ndb
from passlib.context import CryptContext
from webapp2_extras.appengine.auth.models import Unique
import datetime
import json
import logging
import os
import re

from .model import Model
import config
import mailchimp
import mandrill
import searchable_properties as sndb
import util


class BadPassword(Exception):
    """Password doesn't match required pattern."""
    pass


class DuplicateUser(Exception):
    """A user with the provided email already exists."""
    pass


class UserImage(Model):
    """Model for associating users with uploaded images."""

    user_id = ndb.StringProperty(required=True)
    blob_key = ndb.BlobKeyProperty(required=True)


class User(Model):
    """Serve as root entities for Comments and Practices."""

    # see config.auth_types
    last_login = sndb.DateTimeProperty(auto_now_add=True)
    auth_id = sndb.StringProperty(
        required=True, validator=lambda prop, value: value.lower())
    facebook_id = sndb.StringProperty(default=None, search_type=search.TextField)
    google_id = sndb.StringProperty(default=None, search_type=search.TextField)
    hashed_password = sndb.StringProperty(default=None)
    first_name = sndb.StringProperty(default='', search_type=search.TextField)
    last_name = sndb.StringProperty(default='', search_type=search.TextField)
    email = sndb.StringProperty(
        required=True, validator=lambda prop, value: value.lower(), search_type=search.TextField)
    is_admin = sndb.BooleanProperty(default=False)
    receives_updates = sndb.BooleanProperty(default=True)
    image_url = sndb.StringProperty(default='')
    short_bio = sndb.StringProperty(default='')
    # Username for display
    username = sndb.StringProperty(search_type=search.TextField)
    # Username for uniqueness checking
    canonical_username = sndb.ComputedProperty(
        lambda self: self.username.lower() if self.username else '')
    authorship_invites = sndb.StringProperty(repeated=True, default=None)

    # App Engine can only run pure-python external libraries, and so we can't get
    # a native (C-based) implementation of bcrypt. Pure python implementations are
    # so slow that [the feasible number of rounds is insecure][1]. This uses the
    # [algorithm recommended by passlib][2].
    # [1]: http://stackoverflow.com/questions/7027196/how-can-i-use-bcrypt-scrypt-on-appengine-for-python
    # [2]: https://pythonhosted.org/passlib/new_app_quickstart.html#sha512-crypt
    password_hashing_context = CryptContext(
        schemes=['sha512_crypt', 'sha256_crypt'],
        default='sha512_crypt',
        all__vary_rounds=0.1,
        # Can change hashing rounds here. 656,000 is the default.
        # sha512_crypt__default_rounds=656000,
        # sha256_crypt__default_rounds=656000,
    )

    @classmethod
    def create(klass, check_uniqueness=True, **kwargs):
        """Checks email uniqueness before creating; raises DuplicateUser.

        Checking uniqueness always generates a Unique entity (an entity of
        class 'Unique') that permanently reserves the email address. But
        checking is also optional, and can be passed as False for testing.

        See http://webapp-improved.appspot.com/_modules/webapp2_extras/appengine/auth/models.html#User.create_user
        """

        # If no username, generate one!
        if 'username' not in kwargs:
            kwargs['username'] = User.create_username(**kwargs)

        else:
            if User.is_valid_username(kwargs['username']):
                raise InvalidUsername("Invalid username {}. Use only letters, numbers, dashes, and underscores."
                                      .format(kwargs['username']))

        # Check for uniqueness of email and username
        if check_uniqueness:
            uniqueness_key = 'User.email:' + kwargs['email']
            is_unique_email = Unique.create(uniqueness_key)
            if not is_unique_email:
                raise DuplicateUser("There is already a user with email {}."
                                    .format(kwargs['email']))

            uniqueness_key = 'User.username:' + kwargs['username'].lower()
            is_unique_username = Unique.create(uniqueness_key)
            if not is_unique_username:
                # Need to also delete the unused email!
                # To ensure that this works on retry
                is_unique_email.delete()
                raise DuplicateUser("There is already a user with username {}."
                                    .format(kwargs['username']))

        # Register user for the mailchimp list
        should_subscribe = kwargs.pop('should_subscribe', False)
        if should_subscribe is not False:
            fields = {}
            if 'first_name' in kwargs:
                fields['first_name'] = kwargs['first_name']
            if 'last_name' in kwargs:
                fields['last_name'] = kwargs['last_name']
            subscribed = mailchimp.subscribe(kwargs['email'], **fields)
            if subscribed:
                kwargs['receives_updates'] = True

        # Add new user to user full text search index
        kwargs['listed'] = True
        kwargs['created'] = datetime.datetime.now()
        kwargs['modified'] = datetime.datetime.now()
        newUser = super(klass, klass).create(**kwargs)
        index = search.Index(config.user_index)
        index.put(newUser.to_search_document())
        return newUser

    @classmethod
    def hash_password(klass, password):
        if re.match(config.password_pattern, password) is None:
            raise BadPassword(u'Bad password: {}'.format(password))
        return klass.password_hashing_context.encrypt(password)

    @classmethod
    def verify_password(klass, password, hashed_password):
        return (klass.password_hashing_context.verify(password, hashed_password)
                if hashed_password else False)

    @classmethod
    def get_auth_id(klass, auth_type, third_party_id):
        if auth_type not in config.auth_types:
            raise Exception("Invalid auth type: {}.".format(auth_type))

        return '{}:{}'.format(auth_type, third_party_id)

    @property
    def auth_type(self):
        return self.auth_id.split(':')[0]

    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return self.first_name + ' ' + self.last_name
        if self.first_name:
            return self.first_name
        return self.username

    @property
    def profile_image(self):
        return self.image_url or '{}/static/images/default-user.png'.format(
            os.environ['HOSTING_DOMAIN'])

    def set_password(self, new_password):
        """May raise BadPassword."""
        logging.info("Setting new password {} for user {}."
                     .format(new_password, self))

        self.hashed_password = self.hash_password(new_password)

        # Alert the user that their password has been changed.
        mandrill.send(
            to_address=self.email,
            subject="Your BELE Library password has been changed.",
            template="change_password.html",
            template_data={
                'domain': 'https://{}'.format(os.environ['HOSTING_DOMAIN']),
                'year': datetime.date.today().year,
            },
        )

    @classmethod
    def check_email_uniqueness(self, email):
        """Check if email is used"""
        unique = Unique.get_by_id('User.email:' + email.lower())
        return unique is None

    @classmethod
    def check_username_uniqueness(self, username):
        """Check if username is used"""
        unique = Unique.get_by_id('User.username:' + username.lower())
        return unique is None

    @classmethod
    def is_valid_username(self, username):
        regex = re.compile('[^A-Za-z0-9\-\_]')
        return username != regex.sub('', username)

    @classmethod
    def create_username(klass, **kwargs):
        unformatted_username = ''
        if 'first_name' in kwargs and 'last_name' in kwargs:
            if kwargs['last_name'] is not None:
                unformatted_username = kwargs['first_name'] + kwargs['last_name']
            else:
                unformatted_username = kwargs['first_name']
        elif 'email' not in kwargs:
            logging.error(u"User doesn't have an email address {}".format(kwargs))
        else:
            unformatted_username = kwargs['email'].split('@')[0]
        regex = re.compile('[^A-Za-z0-9\-\_]')
        username = regex.sub('', unformatted_username)
        if not User.check_username_uniqueness(username):
            # If not unique, iterate through available names
            raw_username = username
            for n in range(1, 1000):
                username = raw_username + str(n)
                if User.check_username_uniqueness(username):
                    break
                if n == 999:
                    raise Exception("No unique username found after 1000 tries.")
        return username

    @classmethod
    def set_subscription(self, email, should_subscribe):
        """Sets user's subscription status to Update List on mailchimp
        """
        # Use 'resubscribe' and 'unsubscribe' methods
        if should_subscribe is True:
            subscribed = mailchimp.resubscribe(email)
            # if resubscription failed, they might not be subscribed at all!
            if not subscribed:
                subscribed = mailchimp.subscribe(email)
        elif should_subscribe is False:
            subscribed = mailchimp.unsubscribe(email)
        return subscribed

    def _post_put_hook(self, value):
        super(User, self)._post_put_hook(value)
        index = search.Index(config.user_index)
        if self.listed:
            index.put(self.to_search_document())
        else:
            index.delete(self.uid)

    def _post_delete_hook(self, key, value):
        search.Index(config.user_index).delete(key.id())
        super(User, self)._post_delete_hook(key, value)

    def update_email(self, email):
        # Remove old email from unique keys so it can be re-used!
        old_email = self.email
        uniqueness_key = 'User.email:' + old_email
        Unique.delete_multi([uniqueness_key])
        # Update to new email and check uniqueness
        setattr(self, 'email', email)
        uniqueness_key = 'User.email:' + email
        unique = Unique.create(uniqueness_key)
        if not unique:
            raise DuplicateField("There is already a user with email {}."
                                 .format(email))
        # Also need to update the user in our mailchimp
        mailchimp.unsubscribe(old_email)
        if self.receives_updates:
            subscribed = mailchimp.subscribe(email)
            # if subscription failed, they might need to resubscribe!
            if not subscribed:
                subscribed = mailchimp.resubscribe(email)
        return unique

    def update_username(self, username):
        if self.username is not None:
            uniqueness_key = 'User.username:' + self.canonical_username
            Unique.delete_multi([uniqueness_key])
        setattr(self, 'username', username)
        uniqueness_key = 'User.username:' + username.lower()
        unique = Unique.create(uniqueness_key)
        if not unique:
            raise DuplicateField("There is already a user with username {}."
                                 .format(username))
        return unique

    def remove_unique_properties(self):
        """Runs on delete to allow email and username to be reused."""
        uniqueness_key_email = 'User.email:' + self.email
        uniqueness_key_username = 'User.username:' + self.username
        Unique.delete_multi([uniqueness_key_email, uniqueness_key_username])

    def add_user_image(self, blob_key):
        """Save dictionary of user image urls.

        Create permenant link to user image --
        You can resize and crop the image dynamically by specifying
        the arguments in the URL '=sxx' where xx is an integer from 0-1600
        representing the length, in pixels, of the image's longest side

        Reference: https://cloud.google.com/appengine/docs/python/images/#Python_Transforming_images_from_the_Blobstore
        """
        image_url = images.get_serving_url(blob_key, secure_url=True)
        self.image_url = image_url

        # Create a UserImage object pointing to blobstore object
        # Reference used for removal of old UserImages
        user_image = UserImage.create(
            user_id=self.uid,
            blob_key=blob_key,
        )
        user_image.put()

    def remove_user_image(self):
        """Removes existing user's image completely"""
        self.image_url = ''

        # Find associated UserImage
        user_image = UserImage.query(user_id=self.uid)

        # Remove permenant link for image
        images.delete_serving_url(user_image.blob_key)

        user_image.deleted = True
        user_image.put()


class ResetPasswordToken(Model):
    """Acts as a one-time-pass for a user to reset their password.

    The "token" is just the uid of a ResetPasswordToken entity.
    """

    user_id = sndb.StringProperty()  # uid string

    def token(self):
        return self.uid

    @classmethod
    def get_user_from_token_string(klass, token_string):
        """Validate a token in a password reset URL.

        Returns:
            * Matching user entity if the token is valid.
            * None if the token doesn't exist or has expired.
        """
        token_entity = ResetPasswordToken.get_by_id(token_string)

        if token_entity is None:
            logging.info("This token doesn't exist: {}.".format(token_string))
            return None

        # Check that it hasn't expired and isn't deleted
        one_hour = datetime.timedelta(hours=1)
        expired = datetime.datetime.now() - token_entity.created > one_hour
        if expired or token_entity.deleted:
            logging.info("This token has expired: {}.".format(token_string))
            return None

        return User.get_by_id(token_entity.user_id)

    @classmethod
    def clear_all_tokens_for_user(klass, user):
        """Delete all tokens for a given user."""
        q = ResetPasswordToken.query(ResetPasswordToken.deleted == False,
                                     ResetPasswordToken.user_id == user.uid)
        tokens = []
        for t in q:
            t.deleted = True
            tokens.append(t)
        ndb.put_multi(tokens)


class AcceptAuthorshipToken(Model):
    """Acts as a one-time-pass for a user to accept authorship to a content entity.

    The "token" is just the uid of an AcceptAuthorshipToken entity.
    """

    user_id = sndb.StringProperty()  # uid string

    def token(self):
        return self.uid

    @classmethod
    def get_user_from_token_string(klass, token_string):
        """Validate a token in an authorship accept URL.

        Returns:
            * Matching user entity if the token is valid.
            * None if the token doesn't exist or has expired.
        """
        token_entity = AcceptAuthorshipToken.get_by_id(token_string)

        if token_entity is None:
            logging.info("This token doesn't exist: {}.".format(token_string))
            return None

        # Check that it hasn't expired and isn't deleted
        one_month = datetime.timedelta(days=30)
        expired = datetime.datetime.now() - token_entity.created > one_month
        if expired or token_entity.deleted:
            logging.info("This token has expired: {}.".format(token_string))
            return None
        return User.get_by_id(token_entity.user_id)

    @classmethod
    def delete(klass, token_string):
        token_entity = AcceptAuthorshipToken.get_by_id(token_string)

        if token_string is None:
            logging.info("This token doesn't exist: {}.".format(token_string))
            return

        token_entity.deleted = True
        token_entity.put()

    @classmethod
    def clear_all_tokens_for_user(klass, user):
        """Delete all tokens for a given user."""
        q = AcceptAuthorshipToken.query(AcceptAuthorshipToken.deleted == False,
                                     AcceptAuthorshipToken.user_id == user.uid)
        tokens = []
        for t in q:
            t.deleted = True
            tokens.append(t)
        ndb.put_multi(tokens)