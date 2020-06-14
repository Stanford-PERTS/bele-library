"""URL Handlers are designed to be simple wrappers over our python API layer.
They generally convert a URL directly to an API function call.
"""

from google.appengine.api import users as app_engine_users
from google.appengine.api import images
from google.appengine.ext import blobstore
from google.appengine.ext import ndb
from google.appengine.ext.webapp import blobstore_handlers
from webapp2_extras.appengine.users import login_required, admin_required
import google.appengine.api.app_identity as app_identity
import collections
import datetime
import json
import logging
import os
import random                           # ForgotPasswordHandler
import re
import string                           # ForgotPasswordHandler
import traceback
import webapp2
import urllib

from api import Api
from base_handler import BaseHandler
from model import (
    AcceptAuthorshipToken,
    BadPassword,
    Book,
    Chapter,
    FileEmbedded,
    Lesson,
    Model,
    Page,
    Practice,
    ResetPasswordToken,
    SecretValue,
    User,
    Vote
)
import config
import util
import mandrill   # Emailing client

# Required for unit testing
from StringIO import StringIO
import sys
import unittest  # python unit testing library
import codecs
import unit_testing  # our unit test cases

# Make sure this is off in production, it exposes exception messages.
debug = util.is_development()

# class ApiHandler(webapp2.RequestHandler):
class ApiHandler(BaseHandler):
    """Superclass for all api-related urls."""

    def dispatch(self, *args, **kwargs):
        """Wrap all api calls in a try/catch so the server never breaks when
        the client hits an api URL."""

        self.response.headers['Content-Type'] = (
            'application/json; charset=utf-8')

        try:
            # Call the descendant handler.
            # super(ApiHandler, self).dispatch()
            BaseHandler.dispatch(self)

        except Exception as error:
            trace = traceback.format_exc()
            # We don't want to tell the public about our exception messages.
            # Just provide the exception type to the client, but log the full
            # details on the server.
            logging.error("{}\n{}".format(error, trace))
            response = {
                'error': True,
                'message': error.__class__.__name__,
            }
            if debug:
                response['message'] = "{}: {}".format(
                    error.__class__.__name__, error)
                response['trace'] = trace
            self.response.write(json.dumps(response))

        else:
            # If everything about the request worked out, but no data was
            # returned, put out a standard empty response.
            if not self.response.body:
                self.write(None)

    def write(self, obj):
        # In the extremely common cases where we want to return an entity or
        # a list of entities, translate them to JSON-serializable dictionaries.
        if isinstance(obj, Model):
            obj = obj.to_client_dict()
        elif type(obj) is list and all([isinstance(x, Model) for x in obj]):
            obj = [x.to_client_dict() for x in obj]
        self.response.write(json.dumps(
            {'error': False, 'data': obj}, default=util.json_dumps_default))

    def process_json_body(self):
        """Enable webob request to accept JSON data in a request body."""

        # This method clears the request body to avoid webapp2 silliness. But
        # that sacrifices idempotence. So save and restore it from a custom
        # attribute.
        if hasattr(self.request, 'original_body'):
            body = self.request.original_body
        else:
            body = self.request.body
            self.request.original_body = body
            # The request object doesn't know how to interpret the JSON in the
            # request body so if we didn't do this, self.request.POST would be
            # full of junk.
            self.request.body = ''

        try:  # Client may not send valid JSON.
            # "Manually" interpret the request payload; webob doesn't know how.
            json_payload = json.loads(body)
        except ValueError:
            # This might be a more traditional foo=bar&baz=quz type payload,
            # so leave it alone; webob can interpret it correctly without help.
            json_payload = None

        return json_payload

    def override_json_body(self, params):
        """Sometimes convenient to change incoming parameters to enforce
        permissions, e.g. in PUT requests which only accept certain
        propeties."""
        self.request.original_body = json.dumps(
            params, default=util.json_dumps_default)

    def get_params(self):
        """Paper over webapp2 weirdness, do type coercion and filtering."""

        # JSON data in POSTs and PUTs require extra work.
        if (self.request.method in ['POST', 'PUT'] and
                'application/json' in self.request.headers['Content-Type']):
            raw_params = self.process_json_body()
        else:
            raw_params = {k: self.request.get(k)
                          for k in self.request.arguments()}

        params = {}
        for k, v in raw_params.items():
            if k in config.ignored_url_arguments:
                continue

            # Convert some special tokens into values that otherwise can't be
            # easily sent in a request string, e.g. None
            if isinstance(v, collections.Hashable) and v in config.url_values:
                v = config.url_values[v]

            if k[-5:] == '_json':
                # this value should be interpreted as json AND renamed w/o suffix
                params[k[:-5]] = json.loads(v)
            elif k in config.boolean_url_arguments:
                # Sending a javascript boolean via POST results in v being a
                # python native bool here. If via GET, it comes as str 'true'.
                if isinstance(v, bool):
                    params[k] = v
                else:
                    params[k] = str(v) in config.true_strings
            elif k in config.integer_url_arguments:
                params[k] = int(v)
            elif k in config.date_url_arguments:
                params[k] = util.parse_datetime(v, 'date')
            elif k in config.datetime_url_arguments:
                params[k] = util.parse_datetime(v, 'datetime')
            elif k in config.list_url_arguments:
                # POST, PUT use json, whereas GET uses separate arguments
                if (self.request.method in ['POST', 'PUT']):
                    if type(v) is list:
                        params[k] = v
                    elif isinstance(v, basestring):
                        params[k] = json.loads(v)
                    else:
                        raise Exception(
                            "Unknown type for list argument {}: {}"
                            .format(k, type(v))
                        )
                else:
                    params[k] = self.request.get_all(k)
            elif k in config.json_url_arguments:
                params[k] = json.loads(v)
            else:
                params[k] = v

        for k, v in params.items():
            if k in config.json_url_arguments_with_numeric_keys:
                params[k] = {int(str_key): val
                             for str_key, val in v.items()}
        return params


class Login(ApiHandler):
    def post(self):
        response = self.authenticate(**self.get_params())
        self.write(response)


class Register(ApiHandler):
    def post(self):
        try:
            response = self.register(**self.get_params())
        except BadPassword:
            response = 'bad_password'
        self.write(response)


class UploadFilesUrl(ApiHandler):
    def get(self):
        user = self.get_current_user()
        patt = r"(?<=\/api\/)\w*(?=\/)"
        entity_type = re.search(patt, self.request.path).group(0)
        # Valid for 10 minutes, to which a user can POST their file to
        # Google Cloud Storage (even though it's using the blobstore API).
        upload_url = blobstore.create_upload_url(
            success_path='/api/{}/upload_files'.format(entity_type),
            gs_bucket_name='{}'.format(util.get_upload_bucket()),
            max_bytes_per_blob=pow(10, 7),  # 10 Megabytes
            max_bytes_total=(5 * pow(10, 7)),  # 50 Megabytes
        )
        self.response.write(json.dumps(
            {'error': False, 'data': upload_url}))


class UploadUserImageUrl(ApiHandler):
    def get(self):
        user = self.get_current_user()

        # The bucket must be created in the app, and it must be set so that all
        # files uploaded to it are public. All of this is easy with the
        # developer's console; look for the three-vertical-dots icon after
        # creating the bucket.
        # bucket = app_identity.get_application_id() + '-upload/user_image'
        bucket = util.get_upload_bucket();

        # Valid for 10 minutes, to which a user can POST their file to
        # Google Cloud Storage (even though it's using the blobstore API).
        upload_url = blobstore.create_upload_url(
            success_path='/api/users/' + user.uid + '/upload_image',
            gs_bucket_name='{}/{}'.format(bucket, user.uid),
            max_bytes_per_blob=pow(10, 7),  # 10 Megabytes
            max_bytes_total=(5 * pow(10, 7)),  # 50 Megabytes
        )
        self.response.write(json.dumps(
            {'error': False, 'data': upload_url}))


class UploadFiles(blobstore_handlers.BlobstoreUploadHandler):
    """Called (from server-side) when a file upload is complete.

    Inherits from a webapp2 convenience class:
    https://cloud.google.com/appengine/docs/python/tools/webapp/blobstorehandlers#BlobstoreUploadHandler
    """

    def post(self):
        self.response.headers['Content-Type'] = (
            'application/json; charset=utf-8')
        entity_id = self.request.get('entity_id')
        entity_type = Model.get_kind(entity_id) if entity_id else None
        # optional entity field param, in case file needs to be written to a specific entity field
        entity_field = self.request.get('entity_field')
        entity_field = entity_field if entity_field else None
        whitelist = ['Practice', 'Book', 'Page']
        # if no entity_id, create entity to store embedded file info before main entity is created
        if entity_type is None:
            entity = FileEmbedded.create()
            logging.info('UploadFiles POST, entity_id={}, entity_type={}, entity={}'.format(entity_id, entity_type, entity))
        elif entity_type not in whitelist:
            logging.error('UploadFiles POST, request entity_type={} is not whitelisted.'.format(entity_type))
            return;
        else:
            entity = globals()[entity_type].get_by_id(entity_id)

        # list of FileInfo objects
        # https://cloud.google.com/appengine/docs/python/blobstore/fileinfoclass
        file_infos = self.get_file_infos()

        # Interesting properties of each FileInfo are:
        props = ['content_type', 'creation', 'filename', 'size', 'md5_hash',
                 'gs_object_name']
        file_dicts = [{k: getattr(f, k) for k in props}
                      for f in file_infos]

        #   Build the file's download link, which will need information on the
        # bucket and GCS object for later retreival of actual content.
        # We'll also need the entity id, which is where we'll store the file
        # name of the object as we want users to receive it (we haven't figured
        # out how to make GCS store human-readable filenames).
        # Note (possible TODO: See if we should use md5 hash instead of object name, see email from chris)
        for f in file_dicts:
            gs_pattern = r'^/gs/(?P<bucket>.+)/(?P<object>.+)$'
            m = re.match(gs_pattern, f['gs_object_name'])
            f['link'] = ('/api/files/{}/{}'
                         .format(entity.uid, m.group('object')))
        logging.info(file_dicts);
        # Save the file meta data to the entity's object as a JSON field.
        if entity_field:
            entity.add_file_data(file_dicts, entity_field)
        else:
            entity.add_file_data(file_dicts)

        entity.put()

        self.response.write(json.dumps(
            {'error': False, 'data': entity.to_client_dict()}))


class UploadUserImage(blobstore_handlers.BlobstoreUploadHandler):
    """Called (from server-side) when a user image upload is complete."""

    def post(self, id):
        # try:
        upload = self.get_uploads()[0]
        blob_key = upload.key()
        user = User.get_by_id(id)

        # Create a url for quick-reference on the user
        user.add_user_image(blob_key=blob_key)
        user.put()

        self.response.write(json.dumps(
            {'error': False, 'data': user.to_client_dict()}))

        # except:
        #     self.response.write(json.dumps(
        #         {'error': True, 'message': 'upload failure'}))


class ViewFile(blobstore_handlers.BlobstoreDownloadHandler):
    """View a file, adding convenient download headers."""
    def get(self, entity_id, gcs_object):
        # get longest side, height and width queries not working
        size = self.request.get('size')
        size_query = '=s' + size if size else None
        # Build the GCS path for this object, which is based on bucket, user,
        # and object.
        entity_type = Model.get_kind(entity_id)
        entity = globals()[entity_type].get_by_id(entity_id)
        gs_object_name = '/gs/{}/{}'.format(
            util.get_upload_bucket(), gcs_object)

        # Although this inherits from webapp's "Blobstore" handler, the files
        # actually reside in Google Cloud Storage. That's why we convert from
        # the gcs file name.
        blob_key = blobstore.create_gs_key(gs_object_name)
        if not blob_key:
            raise Exception("No blob matching {}".format(gs_object_name))

        # Look up the human-readable file name in the file info data of the
        # entity. See the UploadFiles handlers for details on what else is in
        # the file_info dictionary.
        filename = None
        # If there are properties in the entity that contain json files, decode
        # them first
        if hasattr(entity, 'file_props'):
            for file_prop in entity.file_props:

                file_info = getattr(entity, file_prop)
                if file_info == '':
                    logging.info(
                        'entity {} has an empty value for property {}'
                        .format(entity, file_prop)
                    )
                else:
                    file_info = json.loads(file_info)
                    if gs_object_name == file_info['gs_object_name']:
                        filename = file_info['filename']
        if 'files' in entity.json_properties:
            for file_info in entity.json_properties['files']:
                if gs_object_name == file_info['gs_object_name']:
                    filename = file_info['filename']

        if filename is None:
            raise Exception("Could not find file in entity: {} {}"
                            .format(entity_id, gcs_object))
        # Attach headers that make the file 1) immediately download rather than
        # opening in the browser and 2) have a pretty file name.
        self.response.headers['Content-Disposition'] = (
            "attachment; filename=" + str(filename))

        img = None
        try:
            url = images.get_serving_url(blob_key)
            url = url + size_query if size_query else url
            # Read image and requested size
            img = urllib.urlopen(url)
            img = img.read()
            if img is None:
                raise Exception(
                    "Could not read image data from Cloudstore URL: "
                    "{}, blob_key: {}"
                    .format(url, blob_key)
                )
            self.response.write(img)
        except Exception as e:
            logging.info("Couldn't read blob as img. Will try to send_blob().")
            logging.info(e)

        self.send_blob(blob_key)


class ViewUserFile(blobstore_handlers.BlobstoreDownloadHandler):
    """View a file, adding convenient download headers."""
    def get(self, user_id, entity_id, gcs_object):
        size = self.request.get('size')
        size_query = '=s' + size if size else None;
        entity_type = Model.get_kind(entity_id)
        entity = globals()[entity_type].get_by_id(entity_id)
        # Build the GCS path for this object, which is based on bucket, user,
        # and object.
        gs_object_name = '/gs/{}/{}'.format(
            util.get_upload_bucket(), gcs_object)

        # Although this inherits from webapp's "Blobstore" handler, the files
        # actually reside in Google Cloud Storage. That's why we convert from
        # the gcs file name.
        blob_key = blobstore.create_gs_key(gs_object_name)

        # Look up the human-readable file name in the file info data of the
        # practice. See the UploadFiles handlers for details on what else is in
        # the file_info dictionary.
        filename = None
        for file_info in entity.json_properties['files']:
            if gs_object_name == file_info['gs_object_name']:
                filename = file_info['filename']
        if filename is None:
            raise Exception("Could not find file in entity: {} {}"
                            .format(entity_id, gcs_object))
        img = None
        if blob_key:
            url = images.get_serving_url(blob_key)
            url = url + size_query if size_query else url
            # Read image and requested size
            img = urllib.urlopen(url)
            img = img.read()

        if img is None:
            raise Exception("Could not successfully read image data from Cloudstore URL: {}, blob_key: {}"
                            .format(url, blob_key))

        # Attach headers that make the file 1) immediately download rather than
        # opening in the browser and 2) have a pretty file name.
        self.response.headers['Content-Disposition'] = (
            "attachment; filename=" + str(filename))
        self.response.write(img)


class RestfulHandler(ApiHandler):
    """Superclass for all RESTful Model requests
    containers all standard RESTful methods"""

    def rest_get(self, model, id=None):
        params = self.get_params()
        # Check for ID to use for GET
        # ie /practices/<practice_id> vs. /practices
        if id:
            response = self.api.get_by_id(id)
        else:
            response = self.api.get(model, **params)
        self.write(response)
        return response

    def rest_post(self, model, id=None):
        params = self.get_params()
        response = self.api.create(model, **params)
        self.write(response)
        return response

    def rest_put(self, id):
        params = self.get_params()
        response = self.api.update(id, **params)
        self.write(response)
        return response

    def rest_delete(self, id):
        response = self.api.delete(id)
        self.write(response)
        return response

    # Used by Theme and Topic ApiHandlers only
    def remove_child(self, id, child_id):
        parent = self.api.get_by_id(id)
        child = self.api.get_by_id(child_id)
        response = self.api.disassociate(parent, child)
        self.write('Removed')

    def reorder_child(self, id, child_id):
        parent = self.api.get_by_id(id)
        child = self.api.get_by_id(child_id)
        params = self.get_params()
        if 'move_up' in params:
            move_up = params['move_up']
        response = self.api.reorder(parent, child, move_up)
        self.write(response)

    def add_child(self, id, child_id):
        logging.info('add-child')
        parent = self.api.get_by_id(id)
        child = self.api.get_by_id(child_id)
        response = self.api.associate(parent, child)
        self.write('Added')


class Books(RestfulHandler):
    """Handler for all Page Model requests"""

    def get(self, id=None):
        # convert short_uid to uid if needed
        if id is not None:
            id = Book.get_long_uid(id)
            response = self.api.get_by_id(id)
        else:
            params = self.get_params()
            params['order'] = ['-display_order', '-votes_for'];
            books = self.api.get('Book', **params)
            response = []
            author_ids = []
            for b in books:
                author_ids.extend(b.authors)
            author_ids = list(set(author_ids))
            authors = Model.get_by_id(author_ids) or []
            users_by_id = {a.uid: a for a in authors}
            for b in books:
                book_dict = b.to_client_dict()
                book_dict['authors'] = []
                for author_id in b.authors:
                    if author_id in users_by_id:
                        author_dict = users_by_id[author_id].to_client_dict()
                        book_dict['authors'].append(author_dict)
                response.append(book_dict)
        self.write(response)

    def get_popular(self):
        books = Book.get_popular_practices()
        self.write(books)

    def post(self, id=None):
        self.rest_post('Book')

    def put(self, id):
        self.rest_put(id)

    def delete(self, id):
        self.rest_delete(id)

    def remove_file(self, id):
        file_key = self.get_params().get('file')
        if id is not None and file_key is not None:
            id = Book.get_long_uid(id)
            book = self.api.get_by_id(id)
            book.remove_file_data(urllib.unquote(file_key))
            book.put()
            self.write('removed')
        else:
            self.response.write(json.dumps(
                {'error': True, 'message': 'invalid parameters'}))

    def invite_authors(self, id):
        users = self.get_params().get('users')
        if id is not None and users is not None:
            id = Book.get_long_uid(id)
            book = self.api.get_by_id(id)
            users = User.get_by_id(users)
            for u in users:
                current_date = datetime.date.today().strftime("%B %d, %Y")

                # Create a new authorship token
                new_token = AcceptAuthorshipToken.create(user_id=u.uid)
                new_token.put()

                # Send authorship invite email
                mandrill.send(
                    to_address=u.email,
                    subject="Response requested: invitation to collaborate in the BELE Library",
                    template="authorship_email.html",
                    template_data={
                        'domain': 'https://{}'.format(os.environ['HOSTING_DOMAIN']),
                        'entity_id': id,
                        'entity_title': book.title,
                        'entity_type': 'books',
                        'response_date': current_date,
                        'short_name': u.first_name or u.username,
                        'to_address': u.email,
                        'to_uid': u.uid,
                        'token': new_token.token(),
                        'role': 'editor',
                        'year': datetime.date.today().year,
                    },
                )
        else:
            self.response.write(json.dumps(
                {'error': True, 'message': 'invalid parameters'}))

    def remove_author(self, id):
        removee_id = self.get_params().get('user_id')
        if id is None or removee_id is None:
            raise Exception("Invalid parameters.")

        removee = User.get_by_id(removee_id)
        id = Book.get_long_uid(id)
        book = self.api.get_by_id(id)

        remover = self.get_current_user()
        if remover.uid not in book.authors and not remover.is_admin:
            raise Exception("Only authors can remove.")

        if len(book.authors) == 1:
            raise Exception("Can't remove only author.")

        if removee_id in book.authors:
            book.authors.remove(removee_id)
            book.put()

            # Send authorship removal email
            mandrill.send(
                to_address=removee.email,
                subject=u"You're no longer collaborating on {}".format(book.title),
                template="authorship_removal_email.html",
                template_data={
                    'domain': 'https://{}'.format(os.environ['HOSTING_DOMAIN']),
                    'entity_id': id,
                    'entity_title': book.title,
                    'entity_type': 'books',
                    'remover_name': remover.full_name,
                    'remover_email': remover.email,
                    'short_name': removee.first_name or removee.username,
                    'to_address': removee.email,
                    'to_uid': removee.uid,
                    'role': 'editor',
                    'year': datetime.date.today().year,
                },
            )

        self.write(book)

    def add_child(self, id, child_id):
        logging.info('add-child')
        parent = self.api.get_by_id(id)
        child = self.api.get_by_id(child_id)
        response = self.api.associate(parent, child)
        self.write('Added')

    def get_sortable(self, id):
        user = self.get_current_user()
        # convert short_uid to uid if needed
        if id is not None:
            id = Book.get_long_uid(id)
            b = self.api.get_by_id(id)
            chapters_dict = {}
            pages_dict = {}
            chapters = Chapter.get_by_id(b.chapters)
            page_ids = []
            response = []
            chapters = chapters if chapters else []
            for c in chapters:
                chapters_dict[c.uid] = c.to_client_dict()
                page_ids.extend(c.pages)
            pages = Page.get_by_id(page_ids)
            pages = pages if pages else []
            for p in pages:
                pages_dict[p.uid] = p.to_client_dict()
            book = { 'uid': b.uid, 'type': 'book', 'name': b.title }
            chapters_list = []
            if user.uid in b.authors or user.is_admin:
                for chapter_uid in b.chapters:
                    logging.info(u'chapters={}, chapter_uid={}'.format(chapters, chapter_uid))
                    c = chapters_dict[chapter_uid]
                    chapter = { 'uid': c['uid'], 'type': 'chapter', 'name': c['title'], 'short_description': c['short_description'] }
                    pages_list = []
                    for page_uid in c['pages']:
                        p = pages_dict[page_uid]
                        icon_path = p['iconPath'] + '?size=180' if p['iconPath'] else p['iconPath']
                        page = { 'uid': p['uid'], 'type': 'page', 'name': p['title'], 'short_description': p['short_description'], 'iconPath': icon_path }
                        pages_list.append(page)
                    chapter['columns'] = pages_list
                    chapters_list.append(chapter)
                book['columns'] = chapters_list
                response.append(book)
        self.write(response)

    def reorder_chapters(self, id):
        if id is not None:
            id = Book.get_long_uid(id)
            book = self.api.get_by_id(id)
            chapters = self.get_params().get('chapters')
            logging.info('reorder_chapters, original: {}, target: {}'.format(book.chapters, chapters))
            if len(chapters) != len(book.chapters):
                self.response.write(json.dumps(
                    {'error': True, 'message': 'reordering chapters result has different array length'}))
            else:
                book.chapters = chapters;
                book.put()
                self.write('reorder_chapters success')
        else:
            self.response.write(json.dumps(
                {'error': True, 'message': 'invalid parameters'}))


class Chapters(RestfulHandler):
    """Handler for all Page Model requests"""
    def get(self, id=None):
        # convert short_uid to uid if needed
        if id is not None:
            id = Chapter.get_long_uid(id)
            response = self.api.get_by_id(id)
        else:
            user = self.get_current_user()
            params = self.get_params()
            books = self.api.get('Book', **params)
            chapters = self.api.get('Chapter', **params)
            user_chapters = []
            response = []
            for b in books:
                if user.uid in b.authors:
                    user_chapters.extend(b.chapters)
            for c in chapters:
                if c.uid in user_chapters:
                    response.append(c.to_client_dict())
        self.write(response)

    def post(self, id=None):
        self.rest_post('Chapter')

    def put(self, id):
        self.rest_put(id)

    def delete(self, id):
        id = Chapter.get_long_uid(id)
        self.rest_delete(id)

        # Also remove from all books.
        books = (
            Book
            .query()
            .filter(Book.deleted == False)
            .filter(Book.chapters == id)
            .fetch()
        )
        for book in books:
            book.chapters.remove(id)
        ndb.put_multi(books)

    def reorder_pages(self, id):
        if id is not None:
            id = Chapter.get_long_uid(id)
            chapter = self.api.get_by_id(id)
            pages = self.get_params().get('pages')
            logging.info('reorder_pages, original: {}, target: {}'.format(chapter.pages, pages))
            if len(pages) != len(chapter.pages):
                self.response.write(json.dumps(
                    {'error': True, 'message': 'reordering pages result has different array length'}))
            else:
                chapter.pages = pages;
                chapter.put()
                self.write('reorder_pages success')
        else:
            self.response.write(json.dumps(
                {'error': True, 'message': 'invalid parameters'}))


class Pages(RestfulHandler):
    """Handler for all Page Model requests"""

    def get(self, id=None):
        # convert short_uid to uid if needed
        if id is not None:
            id = Page.get_long_uid(id)
            response = self.api.get_by_id(id)
        else:
            params = self.get_params()
            params['order'] = ['-display_order', '-votes_for'];
            pages = self.api.get('Page', **params)
            response = []
            author_ids = []
            for p in pages:
                author_ids.extend(p.authors)
            author_ids = list(set(author_ids))
            authors = Model.get_by_id(author_ids)
            author_dict = {}
            for author in authors:
                author_dict[author.uid] = author
            for p in pages:
                page_authors = []
                for page_author in p.authors:
                    if page_author in author_dict:
                        page_dict = p.to_client_dict()
                        page_authors.append(author_dict[page_author].to_client_dict())
                        page_dict['authors'] = page_authors
                        response.append(page_dict)
                        break
        self.write(response)

    def get_popular(self):
        pages = Page.get_popular_practices()
        self.write(pages)

    def combine_tags(self, params):
        params = params.copy()
        additional_tags = params.get('additional_tags', None)
        if additional_tags is not None:
            to_split = re.sub(r',\s*', ',', additional_tags.strip())
            split_tags = to_split.split(',') if len(to_split) > 0 else []
            all_unique_tags = set(params.get('tags', []) + split_tags)
            params['tags'] = json.dumps(list(all_unique_tags))
            del params['additional_tags']
        return params

    def post(self, id=None):
        params = self.get_params()
        self.override_json_body(self.combine_tags(params))
        self.rest_post('Page')

    def put(self, id):
        params = self.get_params()
        self.override_json_body(self.combine_tags(params))
        self.rest_put(id)

    def delete(self, id):
        id = Page.get_long_uid(id)
        self.rest_delete(id)

        # Also remove from all chapters.
        chapters = self.api.get('Chapter', pages=id)
        for ch in chapters:
            ch.pages.remove(id)
        ndb.put_multi(chapters)

    def remove_file(self, id):
        file_key = self.get_params().get('file')
        if id is not None and file_key is not None:
            id = Page.get_long_uid(id)
            page = self.api.get_by_id(id)
            page.remove_file_data(urllib.unquote(file_key))
            page.put()
            self.write(page)
        else:
            self.response.write(json.dumps(
                {'error': True, 'message': 'invalid parameters'}))

    def invite_authors(self, id):
        users = self.get_params().get('users')
        if id is not None and users is not None:
            id = Page.get_long_uid(id)
            page = self.api.get_by_id(id)
            users = User.get_by_id(users)
            for u in users:
                current_date = datetime.date.today().strftime("%B %d, %Y")

                # Create a new authorship token
                new_token = AcceptAuthorshipToken.create(user_id=u.uid)
                new_token.put()

                # Send authorship invite email
                mandrill.send(
                    to_address=u.email,
                    subject="Response requested: invitation to collaborate in the BELE Library",
                    template="authorship_email.html",
                    template_data={
                        'domain': 'https://{}'.format(os.environ['HOSTING_DOMAIN']),
                        'entity_id': id,
                        'entity_title': page.title,
                        'entity_type': 'pages',
                        'response_date': current_date,
                        'short_name': u.first_name or u.username,
                        'to_address': u.email,
                        'to_uid': u.uid,
                        'token': new_token.token(),
                        'role': 'author',
                        'year': datetime.date.today().year,
                    },
                )
        else:
            self.response.write(json.dumps(
                {'error': True, 'message': 'invalid parameters'}))

    def remove_author(self, id):
        removee_id = self.get_params().get('user_id')
        if id is None or removee_id is None:
            raise Exception("Invalid parameters")

        removee = User.get_by_id(removee_id)
        id = Page.get_long_uid(id)
        page = self.api.get_by_id(id)

        remover = self.get_current_user()
        if remover.uid not in page.authors and not remover.is_admin:
            raise Exception("Only authors can remove.")

        if len(page.authors) == 1:
            raise Exception("Can't remove only author.")

        if removee_id in page.authors:
            page.authors.remove(removee_id)
            page.put()

            # Send authorship removal email
            mandrill.send(
                to_address=removee.email,
                subject=u"You're no longer collaborating on {}".format(page.title),
                template="authorship_removal_email.html",
                template_data={
                    'domain': 'https://{}'.format(os.environ['HOSTING_DOMAIN']),
                    'entity_id': id,
                    'entity_title': page.title,
                    'entity_type': 'books',
                    'remover_name': remover.full_name,
                    'remover_email': remover.email,
                    'short_name': removee.first_name or removee.username,
                    'to_address': removee.email,
                    'to_uid': removee.uid,
                    'role': 'author',
                    'year': datetime.date.today().year,
                },
            )

        self.write(page)


class Practices(RestfulHandler):
    """Handler for all Practice Model requests"""

    def get(self, id=None):
        # convert short_uid to uid if needed
        if id is not None:
            id = Practice.get_long_uid(id)
            response = self.api.get_by_id(id)
        else:
            params = self.get_params()
            practices = self.api.get('Practice', **params)
            user_ids = [p.uid.split('.')[1] for p in practices]
            user_ids = list(set(user_ids))
            response = []
            users = Model.get_by_id(user_ids)
            users = users if users else []
            user_dict = {}
            for user in users:
                user_dict[user.uid] = user;
            for p in practices:
                practice_user = p.uid.split('.')[1]
                if practice_user in user_dict:
                    practice_dict = p.to_client_dict()
                    practice_dict['user'] = user_dict[practice_user].to_client_dict()
                    response.append(practice_dict)
                    break
        self.write(response)

    def get_popular(self):
        practices = Practice.get_popular_practices()
        self.write(practices)

    def post(self, id=None):
        self.rest_post('Practice')

    def put(self, id):
        self.rest_put(id)

    def delete(self, id):
        self.rest_delete(id)

    def remove_file(self, id):
        file_key = self.get_params().get('file')
        if id is not None and file_key is not None:
            id = Practice.get_long_uid(id)
            practice = self.api.get_by_id(id)
            practice.remove_file_data(urllib.unquote(file_key))
            practice.put()
            self.write(practice)
        else:
            self.response.write(json.dumps(
                {'error': True, 'message': 'invalid parameters'}))


class Users(RestfulHandler):
    def get(self, id=None):
        if id is not None:
            id = User.get_long_uid(id)
            response = self.api.get_by_id(id)
        else:
            response = []
            params = self.get_params()
            users = self.api.get('User', **params)
            for u in users:
                response.append(u.to_client_dict())
            if 'n' in params and len(response) == int(params['n']):
                logging.error(
                    "Maxed out users query, authorship invite modal may be "
                    "broken, see issue #92."
                )
        self.write(response)

    def put(self, id):
        self.rest_put(id)

    def get_practices(self, id):
        user_key = Model.id_to_key(id)
        query = Practice.query(ancestor=user_key).filter(Practice.deleted == False).order(-Practice.created)
        # If no user, or not your profile, don't show unlisted
        if not self.api.user or id != self.api.user.uid:
            query = query.filter(Practice.listed == True)

        # Pagination
        n = 20
        params = self.get_params()
        if 'page' in params:
            offset = int(params['page']) * n
        else:
            offset = 0

        self.write(query.fetch(n, offset=offset))

    def get_pages(self, id):
        logging.info('get_pages, id={}'.format(id))
        query = (
            Page
            .query(Page.authors == id)
            .filter(Page.deleted == False)
            .order(-Page.created)
        )
        # If no user, or not your profile, don't show unlisted
        if not self.api.user or id != self.api.user.uid:
            query = query.filter(Page.listed == True)

        # Pagination
        n = 20
        params = self.get_params()
        # TODO: optimization, implement Cursor Queries
        if 'page' in params:
            offset = int(params['page']) * n
        else:
            offset = 0

        self.write(query.fetch(n, offset=offset))

    def get_books(self, id):
        # Query without the api so make sure we get books that are unlisted.
        query = (
            Book
            .query(Book.authors == id)
            .filter(Book.deleted == False)
            .order(-Book.created)
        )
        # If no user, or not your profile, don't show unlisted
        if not self.api.user or id != self.api.user.uid:
            query = query.filter(Page.listed == True)

        # Pagination
        n = 20
        params = self.get_params()
        # TODO: optimization, implement Cursor Queries
        if 'page' in params:
            offset = int(params['page']) * n
        else:
            offset = 0

        self.write(query.fetch(n, offset=offset))

    def get_resources(self, id):
        book_query = Book.query(Book.authors == id).filter(Book.deleted == False).order(-Book.created)
        page_query = Page.query(Page.authors == id).filter(Page.deleted == False).order(-Page.created)
        query = book_query
        # If no user, or not your profile, don't show unlisted
        if not self.api.user or id != self.api.user.uid:
            query = query.filter(Page.listed == True)

        # Pagination
        n = 20
        params = self.get_params()
        # TODO: optimization, implement Cursor Queries
        if 'page' in params:
            offset = int(params['page']) * n
        else:
            offset = 0

        self.write(query.fetch(n, offset=offset))

    def get_votes(self, id):
        # @todo: add pagination
        user_key = Model.id_to_key(id)
        if self.api.user and id == self.api.user.uid:
            query = Vote.query(ancestor=user_key).filter(Vote.deleted == False).order(-Vote.created)

            # Pagination
            n = 20
            params = self.get_params()
            if 'page' in params:
                offset = int(params['page']) * n
            else:
                offset = 0

            votes = query.fetch(n, offset=offset)
            content = []
            for vote in votes:
                if vote.lesson_id is not None:
                    content.append(self.api.get_by_id(vote.lesson_id))
                elif vote.practice_id is not None:
                    content.append(self.api.get_by_id(vote.practice_id))
                elif vote.page_id is not None:
                    content.append(self.api.get_by_id(vote.page_id))
                elif vote.book_id is not None:
                    content.append(self.api.get_by_id(vote.book_id))
            self.write(content)
        else:
            self.response.write(json.dumps(
                {'error': True, 'message': 'Invalid permissions'}))

    def get_authored(self, id):
        # convert short_uid to uid if needed
        user = self.get_current_user()
        params = self.get_params()
        books = self.api.get('Book', **params)
        chapters = self.api.get('Chapter', **params)
        pages = self.api.get('Page', **params)
        response = []
        books_dict = {}
        chapters_dict = {}
        pages_dict = {}

        for b in books:
            books_dict[b.uid] = b.to_client_dict()
        for c in chapters:
            chapters_dict[c.uid] = c.to_client_dict()
        for p in pages:
            pages_dict[p.uid] = p.to_client_dict()

        for b in books:
            book = { 'uid': b.uid, 'type': 'book', 'name': b.title }
            chaptersList = []
            if user.uid in b.authors:
                for chapter_uid in b.chapters:
                    logging.info('chapters={}, chapter_uid={}'.format(chapters, chapter_uid))
                    c = chapters_dict[chapter_uid]
                    chapter = { 'uid': c['uid'], 'type': 'chapter', 'name': c['title'] }
                    pagesList = []
                    for page_uid in c['pages']:
                        p = pages_dict[page_uid]
                        page = { 'uid': p['uid'], 'type': 'page', 'name': p['title'] }
                        pagesList.append(page)
                    chapter['columns'] = pagesList
                    chaptersList.append(chapter)
                book['columns'] = chaptersList
                response.append(book)
        self.write(response)

    def remove_image(self):
        user = self.get_current_user()
        user.remove_user_image()
        user.put()
        self.write(user)


class Themes(RestfulHandler):
    """Handler for all Theme Model requests"""

    def get(self, id=None):
        self.rest_get('Theme', id)

    def post(self, id=None):
        self.rest_post('Theme')

    def put(self, id):
        self.rest_put(id)

    def delete(self, id):
        self.rest_delete(id)

    def get_topics(self, id):
        theme = self.api.get_by_id(id)
        if theme.topics:
            response = self.api.get_by_id(theme.topics)
            self.write(response)
        else:
            self.write('')

    def get_lessons(self, id):
        theme = self.api.get_by_id(id)
        if theme.topics:
            topics = self.api.get_by_id(theme.topics)
            lessons = [lesson for topic in topics for lesson in topic.lessons]
            topic_lessons = self.api.get_by_id(lessons)
            response = topic_lessons
            self.write(response)
        else:
            self.write('')


class Topics(RestfulHandler):
    """Handler for all Topic Model requests"""

    def get(self, id=None):
        self.rest_get('Topic', id)

    def post(self, id=None):
        self.rest_post('Topic')

    def put(self, id):
        self.rest_put(id)

    def get_lessons(self, id):
        topic = self.api.get_by_id(id)
        if topic.lessons:
            response = self.api.get_by_id(topic.lessons)
            self.write(response)
        else:
            self.write('')


class Lessons(RestfulHandler):
    """Handler for all Topic Model requests"""

    def get(self, id=None):
        self.rest_get('Lesson', id)

    def post(self, id=None):
        self.rest_post('Lesson')

    def put(self, id):
        self.rest_put(id)

    def get_themes(self, id):
        lesson = self.api.get_by_id(id)
        if lesson.topics:
            # Get parent topics and themes
            topics = self.api.get_by_id(lesson.topics)
            themes = [theme for topic in topics for theme in topic.themes]
            lesson_themes = self.api.get_by_id(themes)
            response = []
            for theme in lesson_themes:
                theme_dict = theme.to_client_dict()
                topic = None
                for t in topics:
                    if theme.uid in t.themes:
                        topic = t
                if theme.name != 'Growth Mindset for Teachers':
                    theme_dict['lesson_link'] = '/' + theme.short_uid + '/' + topic.short_uid + '/' + lesson.short_uid
                else:
                    theme_dict['lesson_link'] = '/topics/' + topic.short_uid + '/' + lesson.short_uid
                response.append(theme_dict)
            self.write(response)
        else:
            self.write('')


class Comments(RestfulHandler):
    """Handler for all Comment Model requests"""

    def get(self):
        params = self.get_params()
        comments = self.api.get('Comment', **params)
        user_ids = [c.parent_user_id() for c in comments]
        response = []
        users = self.api.get_by_id(user_ids)
        for c in comments:
            for user in users:
                if user.uid == c.parent_user_id():
                    comment_dict = c.to_client_dict()
                    comment_dict['user'] = user.to_client_dict()
                    response.append(comment_dict)
                    break
        self.write(response)

    def post(self):
        self.rest_post('Comment')

    def delete(self, id):
        self.rest_delete(id)


class Votes(RestfulHandler):
    """Handler for all Vote Model requests"""

    def get(self):
        # Fetches votes for currently logged in user
        # Replace lesson_id and practice_id with full versions
        params = self.get_params()
        if 'practice_id' in params:
            params[u'practice_id'] = Practice.get_long_uid(params[u'practice_id'])
        if 'lesson_id' in params:
            params[u'lesson_id'] = Lesson.get_long_uid(params[u'lesson_id'])
        if 'book_id' in params:
            params[u'book_id'] = Book.get_long_uid(params[u'book_id'])
        if 'page_id' in params:
            params[u'page_id'] = Page.get_long_uid(params[u'page_id'])

        votes = self.api.get('Vote', ancestor=self.api.user, **params)
        self.write(votes)

    def post(self):
        self.rest_post('Vote')

    def delete(self, id):
        self.rest_delete(id)


class Feedback(ApiHandler):
    """Handler for all Feedback Model requests"""

    def get(self):
        params = self.get_params()
        response = self.api.get('Feedback', **params)
        self.write(response)

    def post(self):
        params = self.get_params()
        response = self.api.create('Feedback', **params)
        self.write(response)


class Assessments(RestfulHandler):
    """Handler for all Assessment Model requests"""

    def get(self, id=None):
        # convert short_uid to uid if needed
        if id is not None:
            id = Assessment.get_long_uid(id)
            response = self.api.get_by_id(id)
        else:
            params = self.get_params()
            response = self.api.get('Assessment', **params)
        self.write(response)

    def post(self):
        self.rest_post('Assessment')

    def put(self, id):
        self.rest_put(id)

    def delete(self, id):
        self.rest_delete(id)


class SecretValueHandler(ApiHandler):
    """For securely storing secret values."""

    def get(self, id):
        if (not self.api.user.is_admin):
            raise Exception("Permission denied.")
        exists = SecretValue.get_by_id(id) is not None
        self.write({'key exists': exists,
                    'message': "SecretValues can't be read via api urls."})

    def post(self, id):
        if (not self.api.user.is_admin):
            raise Exception("Permission denied.")
        value = self.get_params().get('value', None)
        if value is None:
            raise Exception("Must POST with a value.")
        sv = SecretValue.get_or_insert(id)
        sv.value = value
        sv.put()
        self.write(id)

    def delete(self, id):
        if (not self.api.user.is_admin):
            raise Exception("Permission denied.")
        sv = SecretValue.get_by_id(id)
        if sv is not None:
            sv.key.delete()
        self.write(id)


class SendEmail(RestfulHandler):
    """Handler for sending individual emails."""

    def post(self):
        """Create an email and put it in the sending queue."""
        self.rest_post('Email')


class ForgotPassword(ApiHandler):
    """For public users to send themselves reset-password emails."""
    def get(self):
        # ensure this email address belongs to a known user
        email = self.request.get('email').lower()

        # Look up users by auth_id because that's how they log in;
        # there are other kinds of auth type ('google', 'facebook') that we
        # wouldn't want returned.
        user = User.query(User.auth_id == 'own:' + email).get()

        if user:
            # then this email address is valid; proceed with send

            # deactivate any existing reset tokens
            ResetPasswordToken.clear_all_tokens_for_user(user)

            # create a new token for them
            new_token = ResetPasswordToken.create(user_id=user.uid)
            new_token.put()

            mandrill.send(
                to_address=email,
                subject="Password reset requested.",
                template="forgot_password.html",
                template_data={'token': new_token.token(),
                               'domain': 'https://{}'.format(os.environ['HOSTING_DOMAIN'])},
            )

            logging.info('ForgotPassword queueing an email to: {}'
                         .format(email))

            self.write('sent')

        else:
            logging.info('ForgotPassword invalid email address: {}'
                         .format(email))
            self.write('not_sent')


class ResetPassword(ApiHandler):
    """Uses the tokens in reset password email links to change passwords."""
    def post(self):
        params = self.get_params()

        # Check the token
        user = ResetPasswordToken.get_user_from_token_string(params['token'])
        if user is None:
            self.write('invalid_token')
            return

        # Change the user's password. We're not using api here b/c we're using
        # tokens to authenticate requests rather than sessions. The available
        # api would be 'public' level, which obviously isn't what we want.
        try:
            user.set_password(params['new_password'])
        except BadPassword:
            self.write('bad_password')
            return
        user.put()

        # Clear existing tokens.
        ResetPasswordToken.clear_all_tokens_for_user(user)

        self.write('changed')


class SendReflectionEmail(ApiHandler):
    def post(self):
        params = self.get_params()
        logging.info(
            "Sending reflection email to user with params: {}"
            .format(params)
        )
        current_date = datetime.date.today().strftime("%B %d, %Y")

        # Send rejection message
        mandrill.send(
            to_address=params['to_address'],
            subject="Belonging for Educators - What does belonging look like in my classroom?",
            template="reflection_email.html",
            template_data={
                'questions': params['questions'],
                'reflection': params['reflection'],
                'response_date': current_date,
                'domain': 'https://{}'.format(os.environ['HOSTING_DOMAIN'])},
        )


class GetGoogleLoginLink(ApiHandler):
    def get(self):
        redirect = self.request.get('redirect')
        self.write(app_engine_users.create_login_url(redirect))


class DeleteEverything(ApiHandler):
    """Clears the datastore. Api only allows this on localhost."""
    def get(self):
        self.api.delete_everything()


class Populate(ApiHandler):
    """Create a standard set of entities; useful for testing."""
    def get(self):
        self.api.populate()


class SearchContent(ApiHandler):
    """Search the content index."""
    def get(self):
        query_params = self.get_params()
        logging.info("SearchContent api handler with query params {}"
                     .format(query_params))
        self.write(self.api.search_content(query_params))

class SearchUsers(ApiHandler):
    """Search the content index."""
    def get(self):
        query_params = self.get_params()
        logging.info("SearchUser api handler with query params {}"
                     .format(query_params))
        self.write(self.api.search_users(query_params))


class Content(ApiHandler):
    """Handler for all Comment Model requests"""

    def associate(self):
        # TODO: add backend safety check for whitelisted types.
        params = self.get_params()
        target_index = params.get('index', None)
        move_or_copy = params['move_or_copy']
        if not (params['parent_id'] and params['child_id']):
            return False
        parent_id = params['parent_id']
        child_id = params['child_id']

        [parent, child] = self.api.get_by_id([parent_id, child_id])
        parent_target = '{}s'.format(Model.get_kind(child.uid).lower())
        child_target = '{}s'.format(Model.get_kind(parent.uid).lower())
        parent_items = getattr(parent, parent_target)
        child_items = getattr(child, child_target)

        # Default to placing the child at the end of the list.
        if target_index is None:
            target_index = len(parent_items)

        # Insert child into parent's list of children, order matters.
        if child.uid not in parent_items:
            parent_items.insert(target_index, child.uid)

        # Track what parents a child is a part of. Order doesn't matter.
        if parent.uid not in child_items:
            child_items.append(parent.uid)

        setattr(parent, parent_target, parent_items)
        setattr(child, child_target, child_items)
        logging.info('associate_parent={}'.format(parent))
        logging.info('associate_child={}'.format(child))
        logging.info('at index={}'.format(target_index))
        parent.put()
        child.put()
        self.write('ok')

    def delete_child(self):
        # TODO: add backend safety check for whitelisted types.
        params = self.get_params()
        if not (params['parent_id'] and params['child_id']):
            return False
        parent_id = params['parent_id']
        child_id = params['child_id']
        entites = self.api.get_by_id([])
        [parent, child] = self.api.get_by_id([parent_id, child_id])
        parent_target = '{}s'.format(Model.get_kind(child.uid).lower())
        child_target = '{}s'.format(Model.get_kind(parent.uid).lower())
        parent_items = getattr(parent, parent_target)
        child_items = getattr(child, child_target)
        if child.uid in parent_items:
            parent_items.remove(child.uid)
        if parent.uid in child_items:
            child_items.remove(parent.uid)
        setattr(parent, parent_target, list(set(parent_items)))
        setattr(child, child_target, list(set(child_items)))
        logging.info('delete_child_parent={}'.format(parent))
        logging.info('delete_child_child={}'.format(child))
        parent.put()
        child.put()
        self.write('ok')


# ** Unit Testing ** #


class TestHandler(ApiHandler):
    """Superclass for all unit test urls."""

    def run_test_suite(self, test_suite):
        test_result = unittest.TestResult()

        # To capture print statements while running tests (useful for
        # debugging), replace the normal stdout with our own stream.
        original_stdout = sys.stdout
        sys.stdout = StringIO()

        # Run the tests
        test_result = test_suite.run(test_result)

        # Then capture printed statements so we can return them
        print_statements = sys.stdout.getvalue()

        # Write them to a utf-8 capable std out so we can read them in the logs
        # like normal, if we want to. Normal stdout can't write unicode, see:
        # http://stackoverflow.com/questions/1473577/writing-unicode-strings-via-sys-stdout-in-python
        utf8_stdout = codecs.getwriter('UTF-8')(original_stdout)
        utf8_stdout.write(print_statements)

        # and put things back the way we found them.
        sys.stdout = original_stdout

        return test_result, print_statements

    def test_case_to_dict(self, test_case):
        """Helps with outputting test case results in JSON."""
        # The id is python dot notation for the test method, e.g.
        # test_api_get.ApiGetTest.test_me
        # But, because we use two different discovery methods
        # (loadTestsFromNames() and discover()), they're not precisely the
        # same. This little trick should standardize them.
        test_id = test_case.id()
        bad_prefix = config.unit_test_directory + '.'
        if test_id[:len(bad_prefix)] == bad_prefix:
            test_id = test_id[len(bad_prefix):]
        return {
            'test': test_id,
            # First line of the test method's docstring.
            'description': test_case.shortDescription(),
        }

    def test_result_to_dict(self, test_result, print_statements=''):
        """Helps with outputting test results in JSON.

        See
        https://docs.python.org/2/library/unittest.html#unittest.TestResult"""

        # The structures we're converting to JSON are a weird and variable.
        # Wrangle them into something fully JSON-serializable.
        def stringify(results):
            """Convert all the informative properties of a unittest.TestResult
            object into something our JSON APIs can return."""
            to_return = []

            if len(results) is 0:
                return to_return

            if isinstance(results[0], tuple):
                for test_case, details in results:
                    test_info = self.test_case_to_dict(test_case)
                    test_info['details'] = details
                    to_return.append(test_info)
            elif isinstance(results[0], unittest.TestCase):
                to_return = [self.test_case_to_dict(tc) for tc in results]

            return to_return

        # Run our stringify function on all the weird properties to make a nice
        # dictionary.
        result_dict = {
            'errors': stringify(test_result.errors),
            'failures': stringify(test_result.failures),
            'skipped': stringify(test_result.skipped),
            'expected_failures': stringify(test_result.expectedFailures),
            'unexpected_successes': stringify(test_result.unexpectedSuccesses),
            'tests_run': test_result.testsRun,
            'stdout': print_statements,
        }

        # The was_successful function doesn't do exactly what you expect. It
        # returns True even if there are unexpected successes. Fix it.
        success = (test_result.wasSuccessful() and
                   len(result_dict['unexpected_successes']) is 0)
        result_dict['was_successful'] = success

        return result_dict


class UnitTestAll(TestHandler):
    """Run every test we have."""
    @admin_required
    def get(self):
        test_loader = unittest.loader.TestLoader()
        test_suite = test_loader.discover(config.unit_test_directory)
        test_result, print_statements = self.run_test_suite(test_suite)
        result_dict = self.test_result_to_dict(test_result, print_statements)

        self.write(result_dict)


class UnitTestSome(TestHandler):
    """Run the named tests.

    Use python dot notation to name the tests, see:
    https://docs.python.org/2/library/unittest.html#unittest.TestLoader.loadTestsFromName

    Requires the request variable 'name' for a single name or 'name_json' for
    a list of names. The presence of the second overrides the first.
    """
    @admin_required
    def get(self):
        params = self.get_params()
        if isinstance(params[u'name'], basestring):
            test_names = [params[u'name']]
        elif isinstance(params[u'name'], list):
            test_names = params[u'name']
        else:
            raise Exception("Invalid name: {}.".format(params['name']))

        test_loader = unittest.loader.TestLoader()
        test_suite = test_loader.loadTestsFromNames(test_names, unit_testing)
        test_result, print_statements = self.run_test_suite(test_suite)
        result_dict = self.test_result_to_dict(test_result, print_statements)

        self.write(result_dict)


webapp2_config = {
    'webapp2_extras.sessions': {
        # Related to cookie security, see:
        # http://webapp-improved.appspot.com/api/webapp2_extras/sessions.html
        'secret_key': config.session_cookie_secret_key,
    },
}


application = webapp2.WSGIApplication([
    ('/api/login', Login),
    ('/api/register', Register),
    ('/api/practices', Practices),
    ('/api/pages', Pages),
    ('/api/books', Books),
    ('/api/chapters', Chapters),
    ('/api/users', Users),
    webapp2.Route(r'/api/practices/upload_files', handler=UploadFiles, name='upload_files'),
    webapp2.Route(r'/api/practices/upload_url', handler=UploadFilesUrl, name='upload_files_url'),
    webapp2.Route(r'/api/practices/popular', handler=Practices, name='popular_practices', handler_method='get_popular'),
    webapp2.Route(r'/api/practices/<id>', handler=Practices, name='practice'),
    webapp2.Route(r'/api/practices/<id>/remove_file', handler=Practices, handler_method='remove_file', name='remove-practice-file'),
    webapp2.Route(r'/api/books/upload_files', handler=UploadFiles, name='upload_files'),
    webapp2.Route(r'/api/books/upload_url', handler=UploadFilesUrl, name='upload_files_url'),
    webapp2.Route(r'/api/books/<id>', handler=Books, name='book'),
    webapp2.Route(r'/api/books/<id>/add-child/<child_id>', handler=Books, handler_method='add_child', name='add-book-child'),
    webapp2.Route(r'/api/books/<id>/remove-child/<child_id>', handler=Books, handler_method='remove_child', name='remove-book-child'),
    webapp2.Route(r'/api/books/<id>/reorder-child/<child_id>', handler=Books, handler_method='reorder_child', name='reorder-book-child'),
    webapp2.Route(r'/api/books/<id>/remove_file', handler=Books, handler_method='remove_file', name='remove-book-file'),
    webapp2.Route(r'/api/books/<id>/invite_authors', handler=Books, handler_method='invite_authors', name='invite-book-authors'),
    webapp2.Route(r'/api/books/<id>/get_sortable', handler=Books, handler_method='get_sortable', name='get-sortable'),
    webapp2.Route(r'/api/books/<id>/reorder_chapters', handler=Books, handler_method='reorder_chapters', name='reorder-chapters'),
    webapp2.Route(r'/api/books/<id>/remove_author', handler=Books, handler_method='remove_author', name='remove-book-author'),
    webapp2.Route(r'/api/pages/upload_files', handler=UploadFiles, name='upload_files'),
    webapp2.Route(r'/api/pages/upload_url', handler=UploadFilesUrl, name='upload_files_url'),
    webapp2.Route(r'/api/pages/<id>', handler=Pages, name='page'),
    webapp2.Route(r'/api/pages/<id>/remove_file', handler=Pages, handler_method='remove_file', name='remove-page-file'),
    webapp2.Route(r'/api/pages/<id>/invite_authors', handler=Pages, handler_method='invite_authors', name='invite-page-authors'),
    webapp2.Route(r'/api/pages/<id>/remove_author', handler=Pages, handler_method='remove_author', name='remove-page-author'),
    webapp2.Route(r'/api/chapters/<id>', handler=Chapters, name='chapter'),
    webapp2.Route(r'/api/chapters/<id>/add-child/<child_id>', handler=Chapters, handler_method='add_child', name='add-chapter-child'),
    webapp2.Route(r'/api/chapters/<id>/remove-child/<child_id>', handler=Chapters, handler_method='remove_child', name='remove-chapter-child'),
    webapp2.Route(r'/api/chapters/<id>/reorder-child/<child_id>', handler=Chapters, handler_method='reorder_child', name='reorder-chapter-child'),
    webapp2.Route(r'/api/chapters/<id>/reorder_pages', handler=Chapters, handler_method='reorder_pages', name='reorder-pages'),
    webapp2.Route(r'/api/content/associate', handler=Content, handler_method='associate', name='associate'),
    webapp2.Route(r'/api/content/delete-child', handler=Content, handler_method='delete_child', name='delete_child'),
    webapp2.Route(r'/api/files/<entity_id>/<gcs_object>', ViewFile),
    webapp2.Route(r'/api/files/<user_id>/<entity_id>/<gcs_object>', ViewUserFile),
    webapp2.Route(r'/api/users/<id>/get_authored', handler=Users, handler_method='get_authored', name='get_authored'),
    webapp2.Route(r'/api/users/<id>/upload_image', handler=UploadUserImage, name='upload_user_image'),
    webapp2.Route(r'/api/users/upload_image_url', handler=UploadUserImageUrl, name='upload_user_image_url'),
    webapp2.Route(r'/api/users/remove_image', handler=Users, handler_method='remove_image', name='remove_user_image'),
    webapp2.Route(r'/api/users/<id>', handler=Users, name='user'),
    webapp2.Route(r'/api/users/<id>/practices', handler=Users, handler_method='get_practices', name='user-practices'),
    webapp2.Route(r'/api/users/<id>/pages', handler=Users, handler_method='get_pages', name='user-pages'),
    webapp2.Route(r'/api/users/<id>/books', handler=Users, handler_method='get_books', name='user-books'),
    webapp2.Route(r'/api/users/<id>/votes', handler=Users, handler_method='get_votes', name='user-votes'),
    webapp2.Route(r'/api/users/<id>/resources', handler=Users, handler_method='get_resources', name='user-resources'),
    ('/api/themes', Themes),
    webapp2.Route(r'/api/themes/<id>', handler=Themes, name='theme'),
    webapp2.Route(r'/api/themes/<id>/topics', handler=Themes, handler_method='get_topics', name='theme-topics'),
    webapp2.Route(r'/api/themes/<id>/lessons', handler=Themes, handler_method='get_lessons', name='theme-lessons'),
    webapp2.Route(r'/api/themes/<id>/remove-child/<child_id>', handler=Themes, handler_method='remove_child', name='remove-theme-child'),
    webapp2.Route(r'/api/themes/<id>/reorder-child/<child_id>', handler=Themes, handler_method='reorder_child', name='reorder-theme-child'),
    webapp2.Route(r'/api/themes/<id>/add-child/<child_id>', handler=Themes, handler_method='add_child', name='add-theme-child'),
    ('/api/topics', Topics),
    webapp2.Route(r'/api/topics/<id>', handler=Topics, name='topic'),
    webapp2.Route(r'/api/topics/<id>/lessons', handler=Topics, handler_method='get_lessons', name='topic-lessons'),
    webapp2.Route(r'/api/topics/<id>/remove-child/<child_id>', handler=Topics, handler_method='remove_child', name='remove-topic-child'),
    webapp2.Route(r'/api/topics/<id>/reorder-child/<child_id>', handler=Topics, handler_method='reorder_child', name='reorder-topic-child'),
    webapp2.Route(r'/api/topics/<id>/add-child/<child_id>', handler=Topics, handler_method='add_child', name='add-topic-child'),
    ('/api/lessons', Lessons),
    webapp2.Route(r'/api/lessons/<id>', handler=Lessons, name='lesson'),
    webapp2.Route(r'/api/lessons/<id>/themes', handler=Lessons, handler_method='get_themes', name='lesson-themes'),
    ('/api/comments', Comments),
    webapp2.Route(r'/api/comments/<id>', handler=Comments, name='comment'),
    ('/api/votes', Votes),
    webapp2.Route(r'/api/votes/<id>', handler=Votes, name='vote'),
    ('/api/feedback', Feedback),
    ('/api/email', SendEmail),
    webapp2.Route(r'/api/secret_values/<id>', handler=SecretValueHandler),
    ('/api/forgot_password', ForgotPassword),
    ('/api/reset_password', ResetPassword),
    ('/api/send_reflection_email', SendReflectionEmail),
    ('/api/get_google_login_link', GetGoogleLoginLink),
    ('/api/delete_everything', DeleteEverything),
    ('/api/populate', Populate),
    ('/api/search/users', SearchUsers),
    ('/api/search', SearchContent),
    ('/api/unit_test/all', UnitTestAll),
    ('/api/unit_test/some', UnitTestSome),
], config=webapp2_config, debug=debug)
