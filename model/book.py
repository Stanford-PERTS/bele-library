"""
Book Model
===========

Course content books
"""

from google.appengine.api import search
import config
import datetime
import util
import searchable_properties as sndb
import logging
import mandrill
import json
import os

from .content import Content
from .user import User
from .page import Page


class Book(Content):

    chapters = sndb.StringProperty(repeated=True)  # ordered children
    authors = sndb.StringProperty(repeated=True, search_type=search.TextField)  # unordered children

    book_image = sndb.StringProperty(default='', search_type=search.TextField)
    icon = sndb.StringProperty(default='', search_type=search.TextField)
    status = sndb.StringProperty(default='pending', choices=['draft', 'pending', 'approved', 'rejected', 'deleted']) # enum: draft, pending, approved, or rejected

    acknowledgements = sndb.TextProperty(default='') # up to 1000 chars, HTML
    preferred_citation = sndb.StringProperty(default='') # up to 1000 chars, text

    display_order = sndb.IntegerProperty(default=1,
                                    search_type=search.NumberField)
    votes_for = sndb.IntegerProperty(default=0, search_type=search.NumberField)
    num_comments = sndb.IntegerProperty(default=0, search_type=search.NumberField)
    locale = sndb.StringProperty(default='en')

    # class properties that contain files as json strings
    file_props = ['book_image', 'icon'];

    def add_file_data(self, file_dicts, entity_field='files'):
        """Save dictionaries of uploaded file meta data."""
        entity_fields_whitelist = self.file_props
        if entity_field in entity_fields_whitelist:
            setattr(self, entity_field, json.dumps(file_dicts[0], default=util.json_dumps_default))

    def remove_file_data(self, file_key):
        """Remove file dictionaries from existing json_properties"""
        for prop in self.file_props:
            value = getattr(self, prop)
            value = util.try_parse_json(value)
            # delete file if matches old file, or if new value is empty string
            if value == '' or file_key == value['gs_object_name']:
                setattr(self, prop, '')

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
            if (new_status == 'approved'):
                # Send acceptance message
                # @todo: add name to subject line
                mandrill.send(
                    to_address=author.email,
                    subject="Your book upload is approved!",
                    template="accepted_notification.html",
                    template_data={
                        'short_name': short_name,
                        'full_name': full_name,
                        'entity_name': self.title,
                        'entity_url': '/books/' + self.short_uid,
                        'domain': 'https://{}'.format(os.environ['HOSTING_DOMAIN']),
                        'year': datetime.date.today().year,
                    },
                )

            elif (new_status == 'rejected'):
                # Send rejection message
                mandrill.send(
                    to_address=author.email,
                    subject="We couldn't approve your book...",
                    template="rejected_notification.html",
                    template_data={
                        'short_name': short_name,
                        'full_name': full_name,
                        'entity_name': self.title,
                        'entity_url': '/books/' + self.short_uid,
                        'edit_url': '/books/manage/' + self.short_uid,
                        'domain': 'https://{}'.format(os.environ['HOSTING_DOMAIN']),
                        'year': datetime.date.today().year,
                    },
                )

    def get_chapters_with_pages(self, map_function=None):
        """Return ordered array of page data, organized by chapter"""
        pages_dict = {};
        chapters_dict = {};
        chapters = Chapter.get_by_id(self.chapters)
        if chapters is None:
            return {}
        chapter_pages = []
        page_ids = []
        for chapter in chapters:
            if chapter:
                chapters_dict[chapter.uid] = chapter.to_client_dict()
                page_ids.extend(chapter.pages)
                page_ids = list(set(page_ids))
                pages = Page.get_by_id(page_ids)
                pages = pages if pages is not None else []
                for page in pages:
                    page.icon = util.extract_value_from_json(page.icon, 'link')
                    page.icon = page.icon + '?size=360' if page.icon else page.icon
                    pages_dict[page.uid] = page.to_client_dict()
            # Returns a dict with the page uid and a link to the page detail
            def get_page_dict(page_id):
                page = pages_dict[page_id]
                # page['icon'] = util.extract_value_from_json(page['icon'], 'link')
                return page;

        for c in chapters:
            if c:
                chapter_dict = chapters_dict[c.uid]
                chapter_dict['pages'] = map(lambda page_id: get_page_dict(page_id), c.pages)
                chapter_pages.append(chapter_dict)
        return chapter_pages

class Chapter(Content):

    books = sndb.StringProperty(repeated=True, search_type=search.AtomField)  # unordered parents

    pages = sndb.StringProperty(repeated=True)  # unordered children, max 10

    def put(self, **kwargs):
        if len(self.books) > 0:
            self.listed = Book.get_by_id(self.books[0]).listed

        chapter = super(Chapter, self).put(**kwargs)
        return chapter

    def get_pages(self):
      """Get child pages of a chapter model."""
      page_ids = self.pages
      pages = Page.get_by_id(page_ids)
      return pages

    def associate_pages(self, pages):
        """Takes a list of page objects and adds them to the course
        as an array of children 'chapter.pages_list' if they are a child

        Creates an empty array if none are children of this course
        """
        self.pages_list = []
        for page_uid in self.pages:
            for page in pages:
                # Breaks after match to prevent repeats
                if page.uid == page_uid:
                    self.pages_list.append(topic)
                    # this is used in the ViewHandler to determine associations
                    break

    # def associate_book(self, book_id):
