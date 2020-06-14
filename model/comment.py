"""
Comment Model
===========

Model for commenting on Practices and Lessons;
Always in a group under a user
"""

import logging
import os
import re

import config
import datetime
import util
import mandrill
import searchable_properties as sndb

from .lesson import Lesson
from .model import Model
from .practice import Practice
from .page import Page
from .theme import Theme
from .topic import Topic
from .email import Email
from .user import User


class Comment(Model):
    """Always in a group under a User."""

    body = sndb.TextProperty(default='')
    practice_id = sndb.StringProperty(default=None)
    lesson_id = sndb.StringProperty(default=None)
    page_id = sndb.StringProperty(default=None)
    # Overrides Model's default for this property, which is False. We always
    # want to see comments.
    listed = sndb.BooleanProperty(default=True)

    @classmethod
    def create(klass, **kwargs):
        if ('practice_id' not in kwargs) and ('lesson_id' not in kwargs) and ('page_id' not in kwargs):
            raise Exception('Must specify a practice, lesson, or page when '
                            'creating a comment. Received kwargs: {}'
                            .format(kwargs))
        comment = super(klass, klass).create(**kwargs)

        # For email notifications
        content_url = '/'
        content = None

        if comment.page_id:
            page = Page.get_by_id(comment.page_id)
            if page is not None:
                page.num_comments += 1
                page.put()

                # For email
                content = page
                content_url = '/pages/{}'.format(page.short_uid)

                # Send email to creator
                author_ids = page.authors
                commenter = comment.get_parent_user()
                authors = User.get_by_id(author_ids) or []

                for author in authors:

                    # logic to not email yourself...
                    if author != commenter.email:

                        short_name = author.first_name or ''
                        full_name = author.full_name
                        commenter_image_url = commenter.profile_image

                        # Uses Email model to queue email and prevent spam
                        email = Email.create(
                            to_address=author.email,
                            subject="Someone commented on your BELE Library upload",
                            template="comment_creator_notification.html",
                            template_data={
                                'short_name': short_name,
                                'full_name': full_name,
                                'commenter_name': commenter.full_name,
                                'commenter_image_url': commenter_image_url,
                                'content_name': content.title,
                                'comment_body': comment.body,
                                'content_url': content_url,
                                'domain': 'https://{}'.format(os.environ['HOSTING_DOMAIN']),
                                'year': datetime.date.today().year,
                            },
                        )

                        email.put()

                    # Send email to any users @replied to
                    usernames = re.search('\@(\w+)', comment.body)

                    if usernames is not None:
                        username = usernames.group(0).split('@')[1]

                        # Fetch user from username and send email message
                        replied_to = User.query(User.username == username).fetch(1)
                        if replied_to:
                            replied_to = replied_to[0]

                            short_name = replied_to.first_name or ''
                            full_name = replied_to.full_name
                            commenter_image_url = commenter.profile_image

                            # Uses Email model to queue email and prevent spam
                            email = Email.create(
                                to_address=replied_to.email,
                                subject="Someone replied to you on BELE Library",
                                template="comment_reply_notification.html",
                                template_data={
                                    'short_name': short_name,
                                    'full_name': full_name,
                                    'commenter_name': commenter.full_name,
                                    'commenter_image_url': commenter_image_url,
                                    'content_name': content.title,
                                    'comment_body': comment.body,
                                    'content_url': content_url,
                                    'domain': 'https://{}'.format(os.environ['HOSTING_DOMAIN']),
                                    'year': datetime.date.today().year,
                                },
                            )

                            email.put()

        # Email interested team members that a comment has been created
        mandrill.send(
            to_address=config.comment_recipients,
            subject="New Comment on BELE Library!",
            template="comment_notification.html",
            template_data={'comment': comment,
                           'user': comment.get_parent_user(),
                           'content_name': content.title,
                           'content_url': content_url,
                           'domain': 'https://{}'.format(os.environ['HOSTING_DOMAIN'])},
        )

        logging.info('model.Comment queueing an email to: {}'
                     .format(config.comment_recipients))

        return comment

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
            return 'Comment_{}.User_{}'.format(
                short_or_long_uid[:8], short_or_long_uid[8:])

    def parent_user_id(self):
        return self.key.parent().id()

    def get_parent_user(self):
        return self.key.parent().get()