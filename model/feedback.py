"""
Feedback Model
===========

Publicly postable feedback object
"""

import os
import logging

import config
import util
import mandrill
import searchable_properties as sndb

from .model import Model


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
                subject="BELE Library Feedback!",
                template="feedback_notification.html",
                template_data={'feedback': feedback,
                               'domain': 'https://{}'.format(os.environ['HOSTING_DOMAIN'])},
            )

        logging.info('model.Feedback queueing an email to: {}'
                     .format(config.feedback_recipients))
        

        return feedback