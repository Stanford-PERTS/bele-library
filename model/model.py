"""
Model
===========

Superclass for all other models;
contains generic properties and methods
"""

from google.appengine.api import logservice         # ErrorChecker
from google.appengine.api import search
from google.appengine.ext import ndb
import collections
import json
import logging
import random
import re
import string
import sys

import config
import util
import searchable_properties as sndb


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
    uid = sndb.TextProperty(default=None)
    short_uid = sndb.TextProperty(default=None, search_type=search.AtomField)
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

        # ndb won't recognize the simulated template_data if passed directly
        # as a keyword argument. Translate that too.
        if 'template_data' in kwargs:
            kwargs['template_data_string'] = json.dumps(
                kwargs['template_data'])
            del kwargs['template_data']

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

        kwargs['uid'] = uid
        kwargs['short_uid'] = klass.convert_uid(uid)
        return klass(id=uid, **kwargs)

    @classmethod
    def generate_uid(klass, parent=None, identifier=None, existing=False):
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
            # Check the characters to make sure this could be valid
            if re.match(r'^[A-Za-z0-9\-]+$', short_or_long_uid):
                return klass.generate_uid(identifier=short_or_long_uid)
            else:
                # Original UID is invalid anyway, return None
                None

    @classmethod
    def get_parent_uid(klass, uid):
        """Don't use the datastore; get parent ids based on convention."""
        if '.' not in uid:
            raise Exception("Can't get parent of id: {}".format(uid))
        return '.'.join(uid.split('.')[1:])

    @classmethod
    def get_kind(klass, obj):
        """Get the kind (class name string) of an entity, key, or id.

        Examples:
        * For a Theme entity, the kind is 'Theme'
        * For the id 'Comment_p46aOHS6.User_80h41Q4c',
          the kind is 'Comment'.
        """
        if isinstance(obj, basestring):
            return str(obj.split('_')[0])
        elif isinstance(obj, Model):
            return obj.__class__.__name__
        elif isinstance(obj, ndb.Key):
            return obj.kind()
        else:
            raise Exception('Model.get_kind() invalid input: {} ({}).'
                            .format(obj, str(type(obj))))

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
            # I don't think we should be blocking code here
            # Problem was occuring when you search a bad id or just None
            # Ex. "/topics/foobar."
            return None
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

        if self.get_kind(self) in config.indexed_models:
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
        if klass.get_kind(key) in config.indexed_models:
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
            if isinstance(v, dict):
                for k2, v2 in output.items():
                    if hasattr(v2, 'isoformat'):
                        output[k][k2] = v2.isoformat()
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

        # kind is not a field, but it's useful as a filter.
        fields.append(search.AtomField(name='kind', value=Model.get_kind(self)))

        return fields

    def to_search_document(self, rank=None):
        fields = self._get_search_fields()
        # Our uid's are already globally unique, so it's fine (as well as
        # extremely convenient) to use them as search document ids as well.
        # N.B. english language hard coded here. If we ever internationalize,
        # will need to be dynamic.
        return search.Document(doc_id=self.uid, fields=fields, rank=rank,
                               language='en')
