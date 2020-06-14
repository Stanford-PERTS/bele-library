"""
ErrorChecker Model
===========

Sends out notifications about errors
"""

from google.appengine.api import logservice         # ErrorChecker
from google.appengine.api import mail
from google.appengine.ext import ndb
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
import searchable_properties as sndb


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
    body = ("BELE Library error:,\n\n"
            "https://console.developers.google.com/project/mindsetkit/logs\n")

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