"""Cron job code."""

from google.appengine.ext import ndb
import cloudstorage

import datetime
import logging

from api import PermissionDenied
from model import (Email, ErrorChecker, Indexer, User)
import config
import util


class Cron:
    """A collection of functions and a permission scheme for running cron jobs.

    Very similar to api.Api."""

    def __init__(self, api):
        """Requires an admin api object."""
        if not api.user.is_admin:
            raise PermissionDenied("Crons must be run as admin.")
        self.api = api

    def check_for_errors(self):
        """Check for new errors - email on error.
        Must be called with internal_api for full permissions.
        See named_model@Index for full description.
        """

        checker = ErrorChecker.get_or_insert('the error checker')
        result = checker.check()
        checker.put()
        return result

    def send_pending_email(self):
        """Send any email in the queue.
        Must be called with internal_api for full permissions.
        See id_model@Email for full description.
        """
        return Email.send_pending_email()

    def assign_usernames(self):
        """Assigns usernames to all existing users without a
        current username
        """
        query = User.query()
        changed_users = []
        for user in query:
            user_dict = user.to_dict()
            if user_dict.get('username') is None:
                user.username = User.create_username(**user_dict)
                changed_users.append(user)
            # Removes bad first_names
            elif 'first_name' in user_dict:
                if '@' in user_dict['first_name']:
                    user.first_name = user_dict['first_name'].split('@')[0]
                    user.username = None
                    changed_users.append(user)
            # Temporary limiting for acceptance
            if len(changed_users) > 40:
                break
        ndb.put_multi(changed_users)
        return changed_users

    def index_all(self):
        """Cron job to index all content. Should only be run as
        a job because it will likely timeout otherwise. Comes in handy
        for production where updates are constantly being made.
        """
        indexer = Indexer.get_or_insert('the-indexer')
        index = indexer.get_index()

        entities = indexer.get_all_content_entities()
        indexed_count = 0
        for entity in entities:
            # Added redundancy (we really don't want these!!)
            if getattr(entity, 'listed') is True:
                index.put(entity.to_search_document())
                indexed_count += 1

        # Update last_check on indexer to now
        now = datetime.datetime.now()
        indexer.last_check = (
            now
        )
        indexer.put()

        return indexed_count

    def index(self):
        """Index content entities for text search.
        Must be called with internal_api for full permissions.
        See named_model@Index for full description.
        """

        indexer = Indexer.get_or_insert('the-indexer')
        index = indexer.get_index()
        # Now and the max modified time of indexed entites
        # will be used to update last_check.  Basically the
        # last check should either be now time if no items
        # were found to update or the age of the last item
        # that was updated.
        #
        # The reason that we cannot always use now time is
        # because we may not index all of the enties between
        # the last check and now if there are many of them.
        now = datetime.datetime.now()
        max_modified_time_of_indexed_entity = None

        # get changes
        changed_entities = indexer.get_changed_content_entities()

        # post changes
        for entity in changed_entities:
            # Added redundancy (we really don't want these!!)
            if getattr(entity, 'listed') is True:
                index.put(entity.to_search_document())

                # Update the most recent modification time for an
                # indexed entity
                if max_modified_time_of_indexed_entity is None:
                    max_modified_time_of_indexed_entity = entity.modified
                else:
                    max_modified_time_of_indexed_entity = max(
                        max_modified_time_of_indexed_entity,
                        entity.modified
                    )

        # Update last_check so that future calls to index no longer
        # try to index these same items.  The logic of what to set
        # last_check to is articulated above.
        any_updates = max_modified_time_of_indexed_entity is not None
        indexer.last_check = (
            now if not
            any_updates
            else max_modified_time_of_indexed_entity
        )
        indexer.put()

        return changed_entities

    def clean_gcs_bucket(self, bucket):
        """Deletes all files in a given GCS bucket.

        Used for emptying out cluttered buckets, like our backup buckets."""

        filenames = [f.filename for f in cloudstorage.listbucket('/' + bucket)]

        files_deleted = []
        for filename in filenames:
            try:
                cloudstorage.delete(filename)
                files_deleted.append(filename)
            except cloudstorage.NotFoundError:
                # We don't care, as long as the bucket winds up empty.
                logging.warning(u"NotFoundError on file {}".format(filename))

        logging.info(u"Files deleted: {}".format(files_deleted))
        return files_deleted
