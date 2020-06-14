"""
Practice Model
===========

Class representing user-uploaded practices
Subclass of Content Model
Always in a group under a user
"""

from google.appengine.api import search
import logging
import os
import config
import random
import util
import mandrill
import searchable_properties as sndb

from .contentOld import Content
from .model import Model


class Practice(Content):
    """Always in a group under a User."""

    mindset_tags = sndb.StringProperty(repeated=True)
    practice_tags = sndb.StringProperty(repeated=True)
    time_of_year = sndb.StringProperty(default='')
    class_period = sndb.StringProperty(default='')
    # Stores the UID of 'associated' content (Theme or Topic)
    # Used to fetch related practices from various pages
    associated_content = sndb.StringProperty(default='')
    type = sndb.StringProperty(default='text', search_type=search.AtomField)
    body = sndb.TextProperty(default='', search_type=search.TextField)
    youtube_id = sndb.StringProperty(default='')
    iframe_src = sndb.StringProperty(default='')
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
        mandrill.send(
            to_address=config.practice_upload_recipients,
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
        if '.' in short_or_long_uid:  # is long
            return short_or_long_uid
        else:  # is short
            return 'Practice_{}.User_{}'.format(
                short_or_long_uid[:8], short_or_long_uid[8:])

    @classmethod
    def get_related_practices(klass, content, count):
        """Fetches practices related to a content object

        Will default to random pratices if none found.
        """
        related_practices = []
        query = Practice.query(
            Practice.deleted == False,
            Practice.listed == True,
        )
        if content.uid:
            if Model.get_kind(content.uid) == 'Practice':
                if content.associated_content:
                    query = query.filter(Practice.associated_content == content.associated_content)
                query = query.filter(Practice.uid != content.uid)
            else:
                query = query.filter(Practice.associated_content == content.uid)
        query.order(-Practice.created)
        # Pull a 'bucket' of practices to sample from
        related_practices_bucket = query.fetch(15)
        # Only return a random selection of the practices
        if len(related_practices_bucket) > count:
            related_practices = random.sample(related_practices_bucket, count)
        elif len(related_practices_bucket) <= 0:
            related_practices = []
        else:
            related_practices = related_practices_bucket
        return related_practices

    @classmethod
    def get_popular_practices(klass):
        """Fetches popular practices to display on landing page

        @todo: figure out a way to generate this list
        - Possibly adding a field to practices and flagging x practices / week
        - Needs more discussion
        """
        practices = []
        query = Practice.query(
            Practice.deleted == False,
            Practice.listed == True,
            Practice.promoted == True,)
        query.order(-Practice.created)
        practices = query.fetch(20)
        if len(practices) > 6:
            practices = random.sample(practices, 6)
        return practices

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

    def check_status_update(self, **kwargs):
        """Checks the status of an updated practice to determine if the creator
        should be notified of approval or rejection

        Only triggered if pending set from True to False (prevents duplicates)
        """
        if (self.pending is True and kwargs.get('pending') is False):

            creator = self.get_parent_user()
            short_name = creator.first_name if creator.first_name else ''
            full_name = creator.full_name
            if (self.listed is False and kwargs.get('listed') is True):
                # Send acceptance message
                # @todo: add name to subject line
                mandrill.send(
                    to_address=creator.email,
                    subject="Your practice upload is approved!",
                    template="accepted_notification.html",
                    template_data={
                        'short_name': short_name,
                        'full_name': full_name,
                        'practice_name': self.name,
                        'practice_url': '/practices/' + self.short_uid,
                        'domain': os.environ['HOSTING_DOMAIN']},
                )

            else:
                # Send rejection message
                mandrill.send(
                    to_address=creator.email,
                    subject="We couldn't approve your practice...",
                    template="rejected_notification.html",
                    template_data={
                        'short_name': short_name,
                        'full_name': full_name,
                        'practice_name': self.name,
                        'practice_url': '/practices/' + self.short_uid,
                        'edit_url': '/practices/edit/' + self.short_uid,
                        'domain': os.environ['HOSTING_DOMAIN']},
                )

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
