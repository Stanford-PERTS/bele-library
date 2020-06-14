"""The Mindset Kit data model."""

from google.appengine.api import logservice         # ErrorChecker
from google.appengine.api import mail
from google.appengine.api import search
from google.appengine.api import users as app_engine_users
from google.appengine.api import images
from google.appengine.ext import ndb
from webapp2_extras.appengine.auth.models import Unique
import calendar                                     # converts datetime to utc
import collections
import datetime
import itertools
import jinja2
import json
import logging
import os
import markdown
import random
import re
import string
import sys

import config
import util
import mandrill
import searchable_properties as sndb


class IdError(Exception):
    """Used when there is a problem looking something up by id."""
    pass


class DuplicateUser(Exception):
    """A user with the provided email already exists."""
    pass


class Model(ndb.Model):
    """Superclass for all others; contains generic properties and methods."""

    # This id is an encoding of the entity's key. For root entities (those
    # with no ancestors), it's a class name (same as a GAE "kind") and
    # an identifier separated by an underscore.
    # Example: Theme_mW4iQ4cO
    # For entities in a group (those with ancestors), their full heirarchy is
    # encoded, ending with the root entity, separated by periods.
    # Example: Comment_p46aOHS6.User_80h41Q4c
    # An id is always sufficient to look up an entity directly.
    # N.B.: We can't just call it 'id' because that breaks ndb.
    uid = sndb.ComputedProperty(lambda self: self.key.id())
    short_uid = sndb.ComputedProperty(
        lambda self: self.convert_uid(self.key.id()),
        search_type=search.AtomField)
    deleted = sndb.BooleanProperty(default=False)
    created = sndb.DateTimeProperty(auto_now_add=True,
                                    search_type=search.DateField)
    modified = sndb.DateTimeProperty(auto_now=True,
                                     search_type=search.DateField)
    listed = sndb.BooleanProperty(default=False)

    # Do NOT use sndb.JsonProperty here! That stores the data as a blob, which
    # is DROPPED upon export to BigQuery. Instead, this stores the JSON as a
    # string, which you can cleanly asscess as a python object through the
    # `json_properties` property, below.
    json_properties_string = sndb.TextProperty(default='{}')

    @property
    def json_properties(self):
        return json.loads(self.json_properties_string)

    @json_properties.setter
    def json_properties(self, value):
        self.json_properties_string = json.dumps(
            value, default=util.json_dumps_default)
        return value

    @classmethod
    def create(klass, **kwargs):
        # ndb expects parents to be set with a key, but we find it more
        # convenient to pass in entities. Do the translation here.
        if 'parent' in kwargs:
            parent = kwargs['parent']  # used in id generation
            kwargs['parent'] = kwargs['parent'].key
        else:
            parent = None

        if 'id' in kwargs:
            # User has supplied their own id. That's okay (it makes certain
            # URLs nice and readable), but it's not a real uid yet b/c it
            # doesn't adhere to our ClassName_identifierXYZ convention. We'll
            # pass it into generated_uid() later.
            identifier = kwargs['id']
            del kwargs['id']
        else:
            identifier = None

        # ndb won't recognize the simulated json_properties if passed directly
        # as a keyword argument. Translate that too.
        if 'json_properties' in kwargs:
            kwargs['json_properties_string'] = json.dumps(
                kwargs['json_properties'])
            del kwargs['json_properties']

        # Make sure id is unique, otherwise "creating" this entity will
        # overwrite an existing one, which could be a VERY hard bug to chase
        # down.
        for x in range(5):
            uid = klass.generate_uid(parent, identifier)
            existing_entity = Model.get_by_id(uid)
            if not existing_entity:
                break
        if existing_entity:
            if identifier:
                raise Exception("Entity {} already exists.".format(uid))
            else:
                raise Exception("After five tries, could not generate a "
                                "unique id. This should NEVER happen.")

        return klass(id=uid, **kwargs)

    @classmethod
    def generate_uid(klass, parent=None, identifier=None):
        """Make a gobally unique id string, e.g. 'Program_mW4iQ4cO'.

        Using 8 random chars, if we made 10,000 entities of the same kind (and
        comments by a single user count as a kind), the probability of
        duplication is 2E-7. Combined with the five attempts at uniqueness
        in Model.create(), chances of duplication are essentially nil.
        http://en.wikipedia.org/wiki/Universally_unique_identifier#Random_UUID_probability_of_duplicates

        If a parent entity is specified, it becomes part of the uid, like this:
        Comment_p46aOHS6.User_80h41Q4c

        If an identifier is specified, it is used instead of random characters:
        Theme_growth-mindset-is-cool
        """
        if identifier:
            if not re.match(r'^[A-Za-z0-9\-]+$', identifier):
                raise Exception("Invalid identifier: {}. Letters, numbers, "
                                "and hyphens only.".format(identifier))
            suffix = identifier
        else:
            chars = (string.ascii_uppercase + string.ascii_lowercase +
                     string.digits)
            suffix = ''.join(random.choice(chars) for x in range(8))
        uid = klass.__name__ + '_' + suffix

        # Because comments exist as descendants of other entities, a simple
        # id-as-key-name is insufficient. We must store information about its
        # ancestry as well. Example:
        # Comment_p46aOHS6.User_80h41Q4c
        if parent:
            uid += '.' + parent.uid

        return uid

    @classmethod
    def convert_uid(klass, short_or_long_uid):
        """Changes long-form uid's to short ones, and vice versa.

        Long form example: Theme_growth-mindset-is-cool
        Short form exmaple: growth-mindset-is-cool
        """
        if '_' in short_or_long_uid:
            return short_or_long_uid.split('_')[1]
        else:
            return klass.generate_uid(identifier=short_or_long_uid)

    @classmethod
    def get_long_uid(klass, short_or_long_uid):
        """Changes short or long-form uid's to long ones.

        Long form example: Theme_growth-mindset-is-cool
        Short form exmaple: growth-mindset-is-cool
        """
        if '_' in short_or_long_uid:
            return short_or_long_uid
        else:
            return klass.generate_uid(identifier=short_or_long_uid)

    @classmethod
    def get_kind(klass, entity_or_id):
        """Get the kind (same as the class name string) of an entity or id.

        Examples:
        * For a Theme entity, the kind is 'Theme'
        * For the id 'Comment_p46aOHS6.User_80h41Q4c',
          the kind is 'Comment'.
        """
        if isinstance(entity_or_id, basestring):
            return str(entity_or_id.split('_')[0])
        elif isinstance(entity_or_id, Model):
            return entity_or_id.__class__.__name__
        else:
            raise Exception('Model.get_kind() invalid input: {} ({}).'
                            .format(entity_or_id, str(type(entity_or_id))))

    @classmethod
    def get_class(klass, kind):
        """Convert a class name string (same as a GAE kind) to a class.

        See http://stackoverflow.com/questions/1176136/convert-string-to-python-class-object
        """
        return getattr(sys.modules['model'], kind, None)

    @classmethod
    def id_to_key(klass, id):
        parts = id.split('.')
        pairs = [(Model.get_kind(p), '.'.join(parts[-x:]))
                 for x, p in enumerate(parts)]
        return ndb.Key(pairs=reversed(pairs))

    @classmethod
    def get_by_id(klass, id_or_list):
        """The main way to get entities with known ids.

        Args:
            id_or_list: A single perts id string, or a list of such strings,
                of any kind or mixed kinds.
        Returns an entity or list of entities, depending on input.
        """

        # Sanitize input to a list of strings.
        if type(id_or_list) in [str, unicode]:
            ids = [id_or_list]
        elif type(id_or_list) is list:
            ids = id_or_list
        else:
            raise Exception("Invalid id / id: {}.".format(
                id_or_list))

        # Iterate through the list, generating a key for each id
        keys = []
        for id in ids:
            keys.append(Model.id_to_key(id))
        results = ndb.get_multi(keys)

        # Wrangle results into expected structure.
        if len(results) is 0:
            return None
        if type(id_or_list) in [str, unicode]:
            return results[0]
        if type(id_or_list) is list:
            return results

    def __str__(self):
        """A string represenation of the entity. Goal is to be readable.

        Returns, e.g. <id_model.User User_oha4tp8a>.
        Native implementation does nothing useful.
        """
        return '<{}>'.format(self.key.id())

    def __repr__(self):
        """A unique representation of the entity. Goal is to be unambiguous.

        But our ids are unambiguous, so we can just forward to __str__.

        Native implemention returns a useless memory address, e.g.
            <id_model.User 0xa5e418cdd>
        The big benefit here is to be able to print debuggable lists of
        entities, without need to manipulate them first, e.g.
            print [entity.id for entity in entity_list]
        Now you can just write
            print entity_list
        """
        return self.__str__()

    # special methods to allow comparing entities, even if they're different
    # instances according to python
    # https://groups.google.com/forum/?fromgroups=#!topic/google-appengine-python/uYneYzhIEzY
    def __eq__(self, value):
        """Allows entity == entity to be True if keys match.

        Is NOT called by `foo is bar`."""
        if self.__class__ == value.__class__:
            return self.key.id() == value.key.id()
        else:
            return False

    # Because we defined the 'equals' method, eq, we must also be sure to
    # define the 'not equals' method, ne, otherwise you might get A == B is
    # True, and A != B is also True!
    def __ne__(self, value):
        """Allows entity != entity to be False if keys match."""
        if self.__class__ == value.__class__:
            # if they're the same class, compare their keys
            return self.key.id() != value.key.id()
        else:
            # if they're not the same class, then it's definitely True that
            # they're not equal.
            return True

    def __hash__(self):
        """Allows entity in entity_list to be True."""
        return hash(str(self.key))

    def _post_put_hook(self, future):
        """Executes after an entity is put.

        1. Updates search index

        To allow for batch processing (i.e. doing the stuff this function does
        for many entities all at once, instead of doing it here one by one),
        this function can be disabled by adding an emphemeral attribute (one
        not saved to the datastore) to the entity. Example:

            # Don't do post-put processing for these entities, so we can handle
            # them in a batch later.
            for e in entities:
                e.forbid_post_put_hook = True
            ndb.put_multi(entities)
        """
        if getattr(self, 'forbid_post_put_hook', False):
            return

        if isinstance(self, (Lesson, Practice)):
            index = search.Index(config.content_index)
            if self.listed:
                logging.info("Indexing content for search.")
                index.put(self.to_search_document())
            else:
                # Unlisted entities should be actively removed from search.
                logging.info("Removing unlisted content from search.")
                index.delete(self.uid)


    @classmethod
    def _post_delete_hook(klass, key, future):
        """We rarely truely delete entities, but when we do, we prefer Dos
        Equis. I mean, we want to delete them from the search index."""
        if issubclass(klass, Content):
            logging.info("Removing hard-deleted content from search: {}"
                         .format(key.id()))
            search.Index(config.content_index).delete(key.id())

    def to_client_dict(self, override=None):
        """Convert an app engine entity to a dictionary.

        Ndb provides a to_dict() method, but we want to add creature-features:
        1. Put properties in a predictable order so they're easier to read.
        2. Remove or mask certain properties based on the preferences of our
           javascript.
        3. Handle our string-based json_properties correctly.
        4. Ndb (different from db) stores datetimes as true python datetimes,
           which JSON.dumps() doesn't know how to handle. We'll convert them
           to ISO strings (e.g. "2010-04-20T20:08:21.634121")

        Args:
            override: obj, if provided, method turns this object into
                a dictionary, rather than self.
        """
        output = self.to_dict()

        output['json_properties'] = self.json_properties
        del output['json_properties_string']

        for k, v in output.items():
            if hasattr(v, 'isoformat'):
                output[k] = v.isoformat()

        client_safe_output = {}
        for k, v in output.items():
            if k in config.client_private_properties:
                client_safe_output['_' + k] = v
            elif k not in config.client_hidden_properties:
                client_safe_output[k] = v

        # order them so they're easier to read
        ordered_dict = collections.OrderedDict(
            sorted(client_safe_output.items(), key=lambda t: t[0]))

        return ordered_dict

    def _get_search_fields(self):
        fields = []
        klass = self.__class__

        # Scan the properties in entity's class definition for information on
        # how the entity should be converted to a search document. Properties
        # can have search field types defined; we use those to construct the
        # document.
        for prop_name in dir(klass):
            # This is the abstract property object in the class definition.
            # E.g. sndb.StringProperty()
            prop = getattr(klass, prop_name)
            # This is the actual data defined on the entity
            value = getattr(self, prop_name)
            # This is (maybe) the type of search field the property should be
            # converted to.
            search_type = getattr(prop, 'search_type', None)

            # The dir() function iterates all object attributes; only deal with
            # those which 1) are datastore properties, 2) aren't private, and
            # 3) have a search type defined.
            is_field = (isinstance(prop, ndb.model.Property) and
                        not prop_name.startswith('_') and search_type)

            if is_field:
                # Search documents field names aren't unique; storing a list of
                # values means making many fields of the same name. For
                # brevity, make everything as a (possibly single-element) list.
                if not type(value) is list:
                    value = [value]
                for v in value:
                    # It will probably be common to put a boolean in a search
                    # document. The easiest way is to make it a string in an
                    # atom field.
                    if type(v) is bool and search_type is search.AtomField:
                        v = 'true' if v else 'false'
                    fields.append(search_type(name=prop_name, value=v))

        return fields

    def to_search_document(self, rank=None):
        fields = self._get_search_fields()
        # Our uid's are already globally unique, so it's fine (as well as
        # extremely convenient) to use them as search document ids as well.
        # N.B. english language hard coded here. If we ever internationalize,
        # will need to be dynamic.
        return search.Document(doc_id=self.uid, fields=fields, rank=rank,
                               language='en')


class Content(Model):
    """Ancestor class for curated content objects: Theme, Topic, Lesson, and
    Practice.
    """

    name = sndb.StringProperty(required=True, search_type=search.TextField)
    summary = sndb.TextProperty(default='', search_type=search.TextField)
    tags = sndb.StringProperty(repeated=True, search_type=search.AtomField)
    subjects = sndb.StringProperty(repeated=True, search_type=search.AtomField)
    min_grade = sndb.IntegerProperty(default=0,
                                     search_type=search.NumberField)
    max_grade = sndb.IntegerProperty(default=13,
                                     search_type=search.NumberField)
    promoted = sndb.BooleanProperty(default=False,
                                     search_type=search.AtomField)


class Theme(Content):

    topics = sndb.StringProperty(repeated=True)  # ordered children
    color = sndb.StringProperty(default='#666666')
    estimated_duration = sndb.IntegerProperty(default=0)
    lesson_count = sndb.IntegerProperty(default=0)
    target_audience = sndb.StringProperty(default=None)
    popular_lessons = sndb.StringProperty(repeated=True)  # ordered children


class Topic(Content):

    themes = sndb.StringProperty(repeated=True)  # unordered parents
    lessons = sndb.StringProperty(repeated=True)  # ordered children
    color = sndb.StringProperty(default='#666666')


class Lesson(Content):

    topics = sndb.StringProperty(repeated=True)  # unordered parents
    popular_in = sndb.StringProperty(repeated=True)  # unordered parents
    type = sndb.StringProperty(default='text', search_type=search.AtomField)
    youtube_id = sndb.StringProperty(default='')
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


class User(Model):
    """Serve as root entities for Comments and Practices."""

    # see config.auth_types
    auth_id = sndb.StringProperty(
        required=True, validator=lambda prop, value: value.lower())
    facebook_id = sndb.StringProperty(default=None)
    google_id = sndb.StringProperty(default=None)
    hashed_password = sndb.StringProperty(default=None)
    first_name = sndb.StringProperty(default='')
    last_name = sndb.StringProperty(default='')
    email = sndb.StringProperty(
        required=True, validator=lambda prop, value: value.lower())
    is_admin = sndb.BooleanProperty(default=False)
    image_url = sndb.StringProperty(default='')
    short_bio = sndb.StringProperty(default='')
    # Username for display
    username = sndb.StringProperty()
    # Username for uniqueness checking
    canonical_username = sndb.ComputedProperty(
        lambda self: self.username.lower() if self.username else '')

    @classmethod
    def create(klass, check_uniqueness=True, **kwargs):
        """Checks email uniqueness before creating; raises DuplicateUser.

        Checking uniqueness always generates a Unique entity (an entity of
        class 'Unique') that permanently reserves the email address. But
        checking is also optional, and can be passed as False for testing.

        See http://webapp-improved.appspot.com/_modules/webapp2_extras/appengine/auth/models.html#User.create_user
        """

        # If no username, generate one!
        if not 'username' in kwargs:
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

        return super(klass, klass).create(**kwargs)

    @classmethod
    def get_auth_id(klass, auth_type, third_party_id):
        if auth_type not in config.auth_types:
            raise Exception("Invalid auth type: {}.".format(auth_type))

        return '{}:{}'.format(auth_type, third_party_id)

    @property
    def auth_type(self):
        return self.auth_id.split(':')[0]

    def set_password(self, new_password):
        """May raise util.BadPassword."""
        logging.info("Setting new password {} for user {}."
                     .format(new_password, self))

        self.hashed_password = util.hash_password(new_password)

        # Alert the user that their password has been changed.
        mandrill.send(
            to_address=self.email,
            subject="Your Mindset Kit password has been changed.",
            template="change_password.html",
        )

        logging.info('User.set_password queueing an email to: {}'
                     .format(self.email))

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

    def update_email(self, email):
        uniqueness_key = 'User.email:' + self.email
        Unique.delete_multi([uniqueness_key])
        setattr(self, 'email', email)
        uniqueness_key = 'User.email:' + email
        unique = Unique.create(uniqueness_key)
        if not unique:
            raise DuplicateField("There is already a user with email {}."
                                .format(email))
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



class Practice(Content):
    """Always in a group under a User."""

    mindset_tags = sndb.StringProperty(repeated=True)
    practice_tags = sndb.StringProperty(repeated=True)
    time_of_year = sndb.StringProperty(default='')
    class_period = sndb.StringProperty(default='')
    type = sndb.StringProperty(default='text', search_type=search.AtomField)
    body = sndb.TextProperty(default='', search_type=search.TextField)
    youtube_id = sndb.StringProperty(default='')
    has_files = sndb.BooleanProperty(default=False,
                                     search_type=search.AtomField)
    pending = sndb.BooleanProperty(default=True)
    votes_for = sndb.IntegerProperty(default=0, search_type=search.NumberField)
    num_comments = sndb.IntegerProperty(default=0,
                                        search_type=search.NumberField)
 

    @classmethod
    def create(klass, **kwargs):
        """Sends email to interested parties.
        """
        practice = super(klass, klass).create(**kwargs)

        # Email interested parties that a practice has been uploaded.
        mandrill.send(to_address=config.practice_upload_recipients,
                subject="Practice Uploaded to Mindset Kit!",
                template="practice_upload_notification.html",
                template_data={'user': practice.get_parent_user(),
                               'practice': practice,
                               'domain': os.environ['HOSTING_DOMAIN']},
            )

        logging.info('model.Practice queueing an email to: {}'
                     .format(config.practice_upload_recipients))

        return practice


    @classmethod
    def convert_uid(klass, short_or_long_uid):
        """Changes long-form uid's to short ones, and vice versa.

        Overrides method provided in Model.

        Long form example: Practice_Pb4g9gus.User_oha4tp8a
        Short form exmaple: Pb4g9gusoha4tp8a
        """
        if '.' in short_or_long_uid:
            parts = short_or_long_uid.split('.')
            return ''.join([x.split('_')[1] for x in parts])
        else:
            return 'Practice_{}.User_{}'.format(
                short_or_long_uid[:8], short_or_long_uid[8:])

    @classmethod
    def get_long_uid(klass, short_or_long_uid):
        """Changes short of long-form uid's to long ones.

        Overrides method provided in Model.

        Long form example: Practice_Pb4g9gus.User_oha4tp8a
        Short form exmaple: Pb4g9gusoha4tp8a
        """
        if '.' in short_or_long_uid: # is long
            return short_or_long_uid
        else: # is short
            return 'Practice_{}.User_{}'.format(
                short_or_long_uid[:8], short_or_long_uid[8:])

    def add_file_data(self, file_dicts):
        """Save dictionaries of uploaded file meta data."""
        jp = self.json_properties

        if 'files' not in jp:
            jp['files'] = []
        jp['files'].extend(file_dicts)

        self.json_properties = jp

        self.has_files = len(jp['files']) > 0

    def remove_file_data(self, file_key):
        """Remove file dictionaries from existing json_properties"""
        jp = self.json_properties
        # Find and remove file from 'files' in json_properties
        if 'files' in jp:
            for index, file_dict in enumerate(jp['files']):
                if file_key == file_dict[u'gs_object_name']:
                    jp['files'].pop(index)

        self.json_properties = jp
        self.has_files = len(jp['files']) > 0

    def get_parent_user(self):
        return self.key.parent().get()

    def to_search_document(self, rank=None):
        """Extends inherited method in Model."""
        fields = super(Practice, self)._get_search_fields()

        # Add information about the parent user to the search document.
        user = self.get_parent_user()
        # Allow for empty first/last names, and default to an empty string.
        if user is not None:
            user_name = ''.join([(user.first_name or ''), (user.last_name or '')])
            fields.append(search.TextField(name='author', value=user_name))

        # Simplify checking for video and file attachments
        if self.has_files:
            fields.append(search.AtomField(name='content_type', value='files'))
        if self.youtube_id != '':
            fields.append(search.AtomField(name='content_type', value='video'))

        return search.Document(doc_id=self.uid, fields=fields, rank=rank,
                               language='en')


class Comment(Model):
    """Always in a group under a User."""

    body = sndb.TextProperty(default='')
    practice_id = sndb.StringProperty(default=None)
    lesson_id = sndb.StringProperty(default=None)
    # Overrides Model's default for this property, which is False. We always
    # want to see comments.
    listed = sndb.BooleanProperty(default=True)

    @classmethod
    def create(klass, **kwargs):
        if ('practice_id' not in kwargs) and ('lesson_id' not in kwargs):
            raise Exception('Must specify either a practice or a lesson when '
                            'creating a comment. Received kwargs: {}'
                            .format(kwargs))
        comment = super(klass, klass).create(**kwargs)

        # For email notifications
        content_url = '/'
        content = None

        # Increment num_comments on Practice or Lesson if success
        if comment.practice_id:
            practice = Practice.get_by_id(comment.practice_id)
            if practice is not None:
                practice.num_comments += 1
                practice.put()

                # For email
                content = practice
                content_url = 'practices/{}'.format(practice.short_uid)

        if comment.lesson_id:
            lesson = Lesson.get_by_id(comment.lesson_id)
            if lesson is not None:
                lesson.num_comments += 1
                lesson.put()
                content = lesson

                # Get first url for lesson for emailing
                topics = Topic.get_by_id(lesson.topics)
                theme = [theme for topic in topics for theme in topic.themes][0]
                lesson_theme = Theme.get_by_id(theme)
                content_url = lesson_theme.short_uid + '/' + topics[0].short_uid + '/' + lesson.short_uid


        # Email interested team members that a comment has been created
        # @todo: email creator of practice as well
        mandrill.send(to_address=config.comment_recipients,
                subject="New Comment on Mindset Kit!",
                template="comment_notification.html",
                template_data={'comment': comment,
                               'user': comment.get_parent_user(),
                               'content': content,
                               'content_url': content_url,
                               'domain': os.environ['HOSTING_DOMAIN']},
            )

        logging.info('model.Comment queueing an email to: {}'
                     .format(config.comment_recipients))

        return comment

    def parent_user_id(self):
        return self.key.parent().id()

    def get_parent_user(self):
        return self.key.parent().get()


class Vote(Model):
    """Always in a group under a User."""

    vote_for = sndb.BooleanProperty(default=True)
    practice_id = sndb.StringProperty(default=None)
    lesson_id = sndb.StringProperty(default=None)

    @classmethod
    def create(klass, **kwargs):
        if ('practice_id' not in kwargs) and ('lesson_id' not in kwargs):
            raise Exception('Must specify either a practice or a lesson when '
                            'creating a vote. Received kwargs: {}'
                            .format(kwargs))
        # Check if user has voted on this entity
        # existing_vote = klass.query(klass.deleted == False, ancestor=**kwargs['parent'].key, )
        # if existing_vote:
        #     raise Exception('Found an existing vote on this entity for '
        #                     'current user. Received kwargs: {}'
        #                     .format(kwargs))

        # Replace lesson_id and practice_id with full versions
        if 'practice_id' in kwargs:
            kwargs[u'practice_id'] = Practice.get_long_uid(kwargs[u'practice_id'])
        if 'lesson_id' in kwargs:
            kwargs[u'lesson_id'] = Lesson.get_long_uid(kwargs[u'lesson_id'])

        vote = super(klass, klass).create(**kwargs)

        # Increment votes_for on Practice or Lesson if success
        if vote.practice_id:
            practice = Practice.get_by_id(vote.practice_id)
            if practice is not None:
                practice.votes_for += 1
                practice.put()
        if vote.lesson_id:
            lesson = Lesson.get_by_id(vote.lesson_id)
            if lesson is not None:
                lesson.votes_for += 1
                lesson.put()

        return vote

    def parent_user_id(self):
        return self.key.parent().id()


class Feedback(Model):
    """Models an individual Feedback entry."""

    body = sndb.StringProperty(required=True)
    email = sndb.StringProperty(default=None)
    path = sndb.StringProperty(default=None)

    @classmethod
    def create(klass, **kwargs):
        feedback = super(klass, klass).create(**kwargs)

        # Email interested parties about new feedback :)
        mandrill.send(to_address=config.feedback_recipients,
                subject="Mindset Kit Feedback!",
                template="feedback_notification.html",
                template_data={'feedback': feedback,
                               'domain': os.environ['HOSTING_DOMAIN']},
            )

        logging.info('model.Feedback queueing an email to: {}'
                     .format(config.feedback_recipients))
        

        return feedback


class UserImage(Model):
    """Model for associating users with uploaded images."""

    user_id = ndb.StringProperty(required=True)
    blob_key = ndb.BlobKeyProperty(required=True)


class Email(Model):
    """An email in a queue (not necessarily one that has been sent).

    Emails have regular fields, to, from, subject, body. Also a send date and
    an sent boolean to support queuing.

    Uses jinja to attempt to attempt to interpolate values in the
    template_data dictionary into the body and subject.

    Body text comes in two flavors: raw text and html. The raw text is
    interpreted as markdown (after jinja processing) to auto-generate the html
    version (templates/email.html is also used for default styles). Which
    version users see depends on their email client.

    Consequently, all emails should be composed in markdown.
    """

    to_address = sndb.StringProperty(required=True)
    from_address = sndb.StringProperty(required=True)
    reply_to = sndb.StringProperty(default=config.from_server_email_address)
    subject = sndb.StringProperty(default="A message from the Mindset Kit")
    body = sndb.TextProperty()
    html = sndb.TextProperty()
    scheduled_date = sndb.DateProperty()
    was_sent = sndb.BooleanProperty(default=False)
    was_attempted = sndb.BooleanProperty(default=False)
    errors = sndb.TextProperty()

    @classmethod
    def create(klass, template_data={}, **kwargs):
        def render(s):
            return jinja2.Environment().from_string(s).render(**template_data)

        kwargs['subject'] = render(kwargs['subject'])
        kwargs['body'] = render(kwargs['body'])

        return super(klass, klass).create(**kwargs)

    @classmethod
    def we_are_spamming(self, email):
        """Did we recently send email to this recipient?"""

        to = email.to_address

        # We can spam admins, like 
        # so we white list them in the config file
        if to in config.addresses_we_can_spam:
            return False

        # We can also spam admins living at a @mindsetkit.org
        if to.endswith('mindsetkit.org'):
            return False

        # Temporary spamming override...
        return False

        since = datetime.datetime.utcnow() - datetime.timedelta(
            days=config.suggested_delay_between_emails)

        query = Email.query(Email.was_sent == True,
                            Email.scheduled_date >= since)

        return query.count(limit=1) > 0

    @classmethod
    def send(self, email):
        if self.we_are_spamming(email):
            logging.error("We are spamming {}:\n{}"
                          .format(email.to_address, email.to_dict()))

        # Note that we are attempting to send so that we don't keep attempting.
        email.was_attempted = True
        email.put()

        # Debugging info
        logging.info(u"sending email: {}".format(email.to_dict()))
        logging.info(u"to: {}".format(email.to_address))
        logging.info(u"subject: {}".format(email.subject))
        logging.info(u"body:\n{}".format(email.body))

        # Make html version if it has not been explicitly passed in.
        if not email.html:
            email.html = (
                jinja2.Environment(loader=jinja2.FileSystemLoader('templates'))
                .get_template('email.html')
                .render({'email_body': markdown.markdown(email.body)})
            )

        # Try to email through App Engine's API.
        mail.send_mail(email.from_address,
                       email.to_address,
                       email.subject,
                       email.body,
                       reply_to=email.reply_to,
                       html=email.html)

        email.was_sent = True
        logging.info("""Sent successfully!""")
        email.put()

    @classmethod
    def fetch_next_pending_email(self):
        to_send = Email.query(
            Email.deleted == False,
            Email.scheduled_date <= datetime.datetime.utcnow(),
            Email.was_sent == False,
            Email.was_attempted == False,
        )

        return to_send.get()

    @classmethod
    def send_pending_email(self):
        """Send the next unsent email in the queue.

        We only send one email at a time; this allows us to raise errors for
        each email and avoid sending some crazy huge mass mail.
        """

        email = self.fetch_next_pending_email()

        if email:
            self.send(email)
            return email
        else:
            return None


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


class ErrorChecker(ndb.Model):
    """
    Check for recent errors using log api

    Design
    The error checker will keep track of how long it has been since a check
    occured and how long since an email alert was sent.

    It will also facilite searching the error log.

    orginal author
    bmh October 2013
    """

    # constants
    # How long will we wait between emails?
    minimum_seconds_between_emails = 60 * 60  # 1 hour
    maximum_requests_to_email = 100     # how long can the log be
    maximum_entries_per_request = 100   # how long can the log be

    # error levels
    level_map = collections.defaultdict(lambda x: 'UNKNOWN')
    level_map[logservice.LOG_LEVEL_DEBUG] = 'DEBUG'
    level_map[logservice.LOG_LEVEL_INFO] = 'INFO'
    level_map[logservice.LOG_LEVEL_WARNING] = 'WARNING'
    level_map[logservice.LOG_LEVEL_ERROR] = 'ERROR'
    level_map[logservice.LOG_LEVEL_CRITICAL] = 'CRITICAL'

    # email stuff
    to_address = config.to_dev_team_email_address
    from_address = config.from_server_email_address
    subject = "Error(s) during calls to: "
    body = ("General Krang,\n\n"
            "The continuing growth of your brain is threatened. More "
            "information is available on the dashboard.\n\n"
            "https://console.developers.google.com/project/mindsetkit/logs\n\n"
            "We haven't taken over the world, YET.\n\n"
            "The Mindset Kit\n")

    # Data
    last_check = sndb.DateTimeProperty()
    last_email = sndb.DateTimeProperty()

    def datetime(self):
        return datetime.datetime.utcnow()

    def to_unix_time(self, dt):
        return calendar.timegm(dt.timetuple())

    def to_utc_time(self, unix_time):
        return datetime.datetime.utcfromtimestamp(unix_time)

    def any_new_errors(self):
        since = self.last_check if self.last_check else self.datetime()
        log_stream = logservice.fetch(
            start_time=self.to_unix_time(since),
            minimum_log_level=logservice.LOG_LEVEL_ERROR
        )

        return next(iter(log_stream), None) is not None

    def get_recent_log(self):
        """ see api
        https://developers.google.com/appengine/docs/python/logs/functions
        """
        out = ""
        since = self.last_check if self.last_check else self.datetime()
        log_stream = logservice.fetch(
            start_time=self.to_unix_time(since),
            minimum_log_level=logservice.LOG_LEVEL_ERROR,
            include_app_logs=True
        )
        requests = itertools.islice(
            log_stream, 0, self.maximum_requests_to_email)

        for r in requests:
            log = itertools.islice(
                r.app_logs, 0, self.maximum_entries_per_request)
            log = [
                self.level_map[l.level] + '\t' +
                str(self.to_utc_time(l.time)) + '\t' +
                l.message + '\n'
                for l in log
            ]
            out = out + r.combined + '\n' + ''.join(log) + '\n\n'

        return out

    def get_error_summary(self):
        """ A short high level overview of the error.

        This was designed to serve as the email subject line so that
        developers could quickly see if an error was a new type of error.

        It returns the resources that were requested as a comma
        seperated string:
        e.g.

            /api/put/pd, /api/...

        see google api
        https://developers.google.com/appengine/docs/python/logs/functions
        """
        # Get a record of all the requests which generated an error
        # since the last check was performed, typically this will be
        # at most one error, but we don't want to ignore other errors if
        # they occurred.
        since = self.last_check if self.last_check else self.datetime()
        log_stream = logservice.fetch(
            start_time=self.to_unix_time(since),
            minimum_log_level=logservice.LOG_LEVEL_ERROR,
            include_app_logs=True
        )
        # Limit the maximum number of errors that will be processed
        # to avoid insane behavior that should never happen, like
        # emailing a report with a googleplex error messages.
        requests = itertools.islice(
            log_stream, 0, self.maximum_requests_to_email
        )

        # This should return a list of any requested resources
        # that led to an error.  Usually there will only be one.
        # for example:
        #   /api/put/pd
        # or
        #   /api/put/pd, /api/another_call
        out = ', '.join(set([r.resource for r in requests]))

        return out

    def should_email(self):
        since_last = ((self.datetime() - self.last_email).seconds
                      if self.last_email else 10000000)
        return since_last > self.minimum_seconds_between_emails

    def mail_log(self):
        body = self.body + self.get_recent_log()
        subject = self.subject + self.get_error_summary()
        mail.send_mail(self.from_address, self.to_address, subject, body)
        self.last_email = self.now
        return (subject, body)

    def check(self):
        self.now = self.datetime()
        should_email = self.should_email()
        new_errors = self.any_new_errors()

        # check for errors
        if new_errors and should_email:
            message = self.mail_log()
        else:
            message = None

        logging.info("any_new_errors: {}, should_email: {}, message: {}"
                     .format(new_errors, should_email,
                             'None' if message is None else message[0]))

        self.last_check = self.now

        # TODO(benjaminhaley) this should return simpler output, ala
        #                     chris's complaint https://github.com/daveponet/pegasus/pull/197/files#diff-281842ae8036e3fcb830df255cd15610R663
        return {
            'email content': message,
            'checked for new errors': should_email
        }


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

    def get_all_content_entities(self):
        Klasses = [Model.get_class(k) for k in ndb.metadata.get_kinds()]
        # Exclude kinds not defined in this file (show up as None in the list)
        # and anything that isn't a Lesson or Practice.
        Klasses = filter(lambda k: k and k in (Lesson, Practice), Klasses) 

        entities = [
            e for klass in Klasses
            for e in (klass.query(getattr(klass, 'listed') == True)
                      .order(getattr(klass, 'modified')))
        ]

        return entities

    def get_changed_content_entities(self):
        Klasses = [Model.get_class(k) for k in ndb.metadata.get_kinds()]
        # Exclude kinds not defined in this file (show up as None in the list)
        # and anything that isn't a Lesson or Practice.
        Klasses = filter(lambda k: k and k in (Lesson, Practice), Klasses)

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
