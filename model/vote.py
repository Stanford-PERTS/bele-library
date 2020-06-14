"""
Vote Model
===========

Indicates votes for Lesson and Practice objects
Always in a group under a User
"""

import os
import logging

import config
import util
import mandrill
import searchable_properties as sndb

from .lesson import Lesson
from .model import Model
from .practice import Practice
from .page import Page
from .book import Book


class Vote(Model):
    """Always in a group under a User."""

    vote_for = sndb.BooleanProperty(default=True)
    practice_id = sndb.StringProperty(default=None)
    lesson_id = sndb.StringProperty(default=None)
    book_id = sndb.StringProperty(default=None)
    page_id = sndb.StringProperty(default=None)
    entity_id = sndb.StringProperty(default=None)
    entity_type = sndb.StringProperty(default=None)

    @classmethod
    def create(klass, **kwargs):

        # if new dynamic entity fields aren't used (deprecated code), create them for now.
        if 'entity_type' in kwargs:
            target_entity_type = kwargs['entity_type'];
        # TODO: fix this, shouldn't need this fallback for prod.
        else:
            simple_whitelist = ['practice', 'lesson', 'book', 'page'];
            for whitelist_type in simple_whitelist:
                id_prop = '{}_id'.format(whitelist_type)
                if id_prop in kwargs:
                    target_entity_type = whitelist_type

        # Get reference for model object from imports based on entity type
        target_model = globals()[target_entity_type.capitalize()]
        # Construct expected id property from entity type
        target_id_property = '{}_id'.format(target_entity_type)

        existing_uid = kwargs[target_id_property]
        # Replace entity_id with full version
        kwargs[target_id_property] = target_model.get_long_uid(existing_uid)

        vote = super(klass, klass).create(**kwargs)

        # Increment votes_for on entity if success
        if hasattr(vote, target_id_property):
            vote_entity_id = getattr(vote, target_id_property)
            entity = target_model.get_by_id(vote_entity_id)
            if entity is not None:
                entity.votes_for += 1
                entity.put()

        return vote

    def parent_user_id(self):
        return self.key.parent().id()