"""
Page Model
===========

Class representing user-uploaded pages
Subclass of Content Model
"""

from google.appengine.api import search
import logging
import os
import config
import datetime
import random
import util
import mandrill
import json
import searchable_properties as sndb

from .content import Content
from .user import User
from .model import Model


OFFICIAL_TAGS = (
  'Framework',
  'External Service',
  'Student Activity',
  'Adult Activity',
  'Diagnostic',
  'Structural Change'
)


class Page(Content):
    ####
    chapters = sndb.StringProperty(repeated=True)  # unordered parents
    authors = sndb.StringProperty(repeated=True, search_type=search.TextField)  # unordered children

    icon = sndb.StringProperty(default='', search_type=search.TextField)
    iconPath = sndb.ComputedProperty(lambda self: util.extract_value_from_json(self.icon, 'link'))

    # "Challenges & Preconditions"
    preconditions_for_success = sndb.TextProperty(default='')  # Up to 10,000 characters, HTML text with ability to include links and images.
    # "Connection to Equity"
    advances_equity = sndb.TextProperty(default='')  # up to 5,000 characters, HTML
    # "Time Required"
    time_required = sndb.StringProperty(default='')  # minutes
    # "Required Materials"
    required_materials = sndb.TextProperty(default='')  # up to 10,000 characters
    # "Associated Measures"
    associated_measures = sndb.TextProperty(default='')  # Up to 5000 characters, HTML
    # "Evidence of Effectiveness"
    evidence_of_effectiveness = sndb.TextProperty(default='')  # Up to 10,000 characters, HTML text with ability to include links and images.
    # "Related BELE Library Pages"
    related_pages = sndb.StringProperty(repeated=True)  # up to 10 related pages.
    # "Optional Contact Information"
    acknowledgements = sndb.TextProperty(default='')  # Up to 5000 characters, HTML
    # "Preferred Citation"
    preferred_citation = sndb.StringProperty(default='')  # Up to 1000 characters, text
    use_license = sndb.StringProperty(default='')

    status = sndb.StringProperty(default='pending', choices=['draft', 'pending', 'approved', 'rejected', 'deleted']) # enum: draft, pending, approved, or rejected
    ####

    mindset_tags = sndb.StringProperty(repeated=True)
    page_tags = sndb.StringProperty(repeated=True)
    time_of_year = sndb.StringProperty(default='')
    class_period = sndb.StringProperty(default='')
    type = sndb.StringProperty(default='text', search_type=search.AtomField)
    body = sndb.TextProperty(default='', search_type=search.TextField)
    youtube_id = sndb.StringProperty(default='')
    iframe_src = sndb.StringProperty(default='')
    has_files = sndb.BooleanProperty(default=False,
                                     search_type=search.AtomField)
    pending = sndb.BooleanProperty(default=True)
    display_order = sndb.IntegerProperty(default=1,
                                    search_type=search.NumberField)
    votes_for = sndb.IntegerProperty(default=0, search_type=search.NumberField)
    num_comments = sndb.IntegerProperty(default=0,
                                        search_type=search.NumberField)

    # class properties that contain files as json strings
    file_props = ['icon']

    @property
    def ui_props(self):
        return {
            'time_required': {
                'default_value': Page.time_required._default,
                'data_prop': 'time_required',
                'scope_prop': 'pageTime',
                'heading_title': 'Time Required',
                'value_suffix': None,
            },
            'required_materials': {
                'default_value': Page.required_materials._default,
                'data_prop': 'required_materials',
                'scope_prop': 'pageMaterials',
                'heading_title': 'Required Materials',
                'value_suffix': None,
            },
            'preconditions_for_success': {
                'default_value': Page.preconditions_for_success._default,
                'data_prop': 'preconditions_for_success',
                'scope_prop': 'pagePreconditions',
                'heading_title': 'Preconditions for Success',
                'value_suffix': None,
            },
            'advances_equity': {
                'default_value': Page.advances_equity._default,
                'data_prop': 'advances_equity',
                'scope_prop': 'advancesEquity',
                'heading_title': 'Connection to Equity',
                'value_suffix': None,
            },
            'evidence_of_effectiveness': {
                'default_value': Page.evidence_of_effectiveness._default,
                'data_prop': 'evidence_of_effectiveness',
                'scope_prop': 'pageEvidence',
                'heading_title': 'Evidence of Effectiveness',
                'value_suffix': None,
            },
            'associated_measures': {
                'default_value': Page.associated_measures._default,
                'data_prop': 'associated_measures',
                'scope_prop': 'pageMeasures',
                'heading_title': 'Associated Measures',
                'value_suffix': None,
            },
            'acknowledgements': {
                'default_value': Page.acknowledgements._default,
                'data_prop': 'acknowledgements',
                'scope_prop': 'pageAcknowledgements',
                'heading_title': 'Acknowledgements',
                'value_suffix': None,
            },
            'preferred_citation': {
                'default_value': Page.preferred_citation._default,
                'data_prop': 'preferred_citation',
                'scope_prop': 'pageCitations',
                'heading_title': 'Preferred Citation',
                'value_suffix': None,
            },
        }

    @classmethod
    def create(klass, **kwargs):
        """Sends email to interested parties.
        """
        page = super(klass, klass).create(**kwargs)

        # Email interested parties that a page has been uploaded.
        # mandrill.send(
        #     to_address=config.page_upload_recipients,
        #     subject="Page Uploaded to Mindset Kit!",
        #     template="page_upload_notification.html",
        #     template_data={'user': page.get_parent_user(),
        #                    'page': page,
        #                    'domain': 'https://{}'.format(os.environ['HOSTING_DOMAIN'])},
        # )

        # logging.info('model.Page queueing an email to: {}'
        #              .format(config.page_upload_recipients))
        logging.info('creating page');
        return page

    @classmethod
    def convert_uid(klass, short_or_long_uid):
        """Changes long-form uid's to short ones, and vice versa.

        Overrides method provided in Model.

        Long form example: Page_Pb4g9gus
        Short form exmaple: Pb4g9gus
        """
        if '_' in short_or_long_uid:
            return ''.join([short_or_long_uid.split('_')[1]])
        else:
            return 'Page_{}'.format(short_or_long_uid[:4]);

    @classmethod
    def get_long_uid(klass, short_or_long_uid):
        """Changes short of long-form uid's to long ones.

        Overrides method provided in Model.

        Long form example: Page_Pb4g9gus.User_oha4tp8a
        Short form exmaple: Pb4g9gusoha4tp8a
        """
        if '_' in short_or_long_uid:  # is long
            return short_or_long_uid
        else:  # is short
            return 'Page_{}'.format(short_or_long_uid[-8:]);

    @classmethod
    def get_popular_pages(klass):
        """Fetches popular pages to display on landing page

        @todo: figure out a way to generate this list
        - Possibly adding a field to pages and flagging x pages / week
        - Needs more discussion
        """
        pages = []
        query = Page.query(
            Page.deleted == False,
            Page.listed == True,
            Page.promoted == True,)
        query.order(-Page.created)
        pages = query.fetch(20)
        if len(pages) > 6:
            pages = random.sample(pages, 6)
        return pages

    def add_file_data(self, file_dicts, entity_field = None):
        """Save dictionaries of uploaded file meta data."""
        # Process specific field json files, specified by entity_field parameter
        entity_fields_whitelist = self.file_props
        if entity_field in entity_fields_whitelist:
            for k, v in file_dicts[0].items():
                if hasattr(v, 'isoformat'):
                    file_dicts[0][k] = v.isoformat()

            setattr(self, entity_field, json.dumps(file_dicts[0], default=util.json_dumps_default))

        jp = self.json_properties

        # Process generic json files if not an entity field
        if entity_field is None:
            if 'files' not in jp:
                jp['files'] = []
            jp['files'].extend(file_dicts)

            self.json_properties = jp

        self.has_files = 'files' in jp and len(jp['files']) > 0

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
        return {}

    def check_status_update(self, **kwargs):
        """Checks the status of an updated page to determine if the creator
        should be notified of approval or rejection.
        """
        new_status = kwargs.get('status', None)
        now_reviewed = new_status in ('approved', 'rejected')
        changing = self.status != new_status
        if not now_reviewed or not changing:
            return

        authors = User.get_by_id(self.authors) or []
        for author in authors:
            short_name = author.first_name or ''
            full_name = author.full_name
            if new_status == 'approved':
                # Send acceptance message
                # @todo: add name to subject line
                mandrill.send(
                    to_address=author.email,
                    subject="Your page upload is approved!",
                    template="accepted_notification.html",
                    template_data={
                        'short_name': short_name,
                        'full_name': full_name,
                        'entity_name': self.title,
                        'entity_url': '/pages/' + self.short_uid,
                        'domain': 'https://{}'.format(os.environ['HOSTING_DOMAIN']),
                        'year': datetime.date.today().year,
                    },
                )

            else:
                # Send rejection message
                mandrill.send(
                    to_address=author.email,
                    subject="We couldn't approve your page...",
                    template="rejected_notification.html",
                    template_data={
                        'short_name': short_name,
                        'full_name': full_name,
                        'entity_name': self.title,
                        'entity_url': '/pages/' + self.short_uid,
                        'edit_url': '/pages/edit/' + self.short_uid,
                        'domain': 'https://{}'.format(os.environ['HOSTING_DOMAIN']),
                        'year': datetime.date.today().year,
                    },
                )

    def to_search_document(self, rank=None):
        """Extends inherited method in Model."""
        fields = super(Page, self)._get_search_fields()

        # Add information about the parent user to the search document.
        for author_id in self.authors:
            author = self.get_by_id(author_id);
            # Allow for empty first/last names, and default to an empty string.
            if author is not None:
                user_name = ''.join([(author.first_name or ''), (author.last_name or '')])
                fields.append(search.TextField(name='author', value=user_name))

        # Simplify checking for video and file attachments
        if self.has_files:
            fields.append(search.AtomField(name='content_type', value='files'))
        if self.youtube_id != '':
            fields.append(search.AtomField(name='content_type', value='video'))

        return search.Document(doc_id=self.uid, fields=fields, rank=rank,
                               language='en')

    def to_client_dict(self):
        d = super(Page, self).to_client_dict()
        official_tags = []
        additional_tags = []
        for tag in d['tags']:
            if tag in OFFICIAL_TAGS:
                official_tags.append(tag)
            else:
                additional_tags.append(tag)
        d['tags'] = official_tags
        d['additional_tags'] = ', '.join(additional_tags)

        return d
