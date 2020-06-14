"""
Email Model
===========

Model for sending queued emails
Uses 'mandrill.py' for sending
"""

from google.appengine.api import mail
import datetime
import jinja2
import logging
import markdown
import json

import config
import util
import searchable_properties as sndb
import mandrill

from .model import Model


class Email(Model):
    """An email in a queue (not necessarily one that has been sent).

    Emails have regular fields, to, from, subject, body. Also a send date and
    an sent boolean to support queuing.

    Uses jinja to attempt to attempt to interpolate values in the
    template_data dictionary into the body and subject.

    Body text comes in two flavors: raw text and html. The raw text is
    interpreted as markdown (after jinja processing) to auto-generate the html
    version (templates/email.html is also used for default styles). Which
    version users see depends on their email client.

    Consequently, all emails should be composed in markdown.
    """

    to_address = sndb.StringProperty(required=True)
    from_address = sndb.StringProperty(default=config.from_server_email_address)
    reply_to = sndb.StringProperty(default=config.from_server_email_address)
    subject = sndb.StringProperty(default="A message from the BELE Library")
    body = sndb.TextProperty()
    html = sndb.TextProperty()
    template = sndb.StringProperty()
    template_data_string = sndb.TextProperty(default='{}')
    scheduled_date = sndb.DateProperty(auto_now_add=True)
    was_sent = sndb.BooleanProperty(default=False)
    was_attempted = sndb.BooleanProperty(default=False)
    errors = sndb.TextProperty()

    @property
    def template_data(self):
        return json.loads(self.template_data_string)

    @template_data.setter
    def template_data(self, value):
        self.template_data_string = json.dumps(
            value, default=util.json_dumps_default)
        return value

    @classmethod
    def create(klass, **kwargs):
        """
        WARNING: Do NOT pass any objects in kwargs['template_data']
        And be sure any associated templates use plain values in jinja code
        """
        email = super(klass, klass).create(**kwargs)
        return email

    @classmethod
    def we_are_spamming(self, email):
        """Did we recently send email to this recipient?
        @todo discuss - I can think of cases where this can be harmful...
        IE 2 different users comment on 2 different uploads from same user
        I guess we should introduce Notifications in the app :)
        """

        to = email.to_address

        # We can spam admins, like 
        # so we white list them in the config file
        if to in config.addresses_we_can_spam:
            return False

        # We can also spam admins living at a @mindsetkit.org
        if to.endswith('mindsetkit.org'):
            return False

        since = datetime.datetime.utcnow() - datetime.timedelta(
            minutes=config.suggested_delay_between_emails)

        query = Email.query(Email.was_sent == True,
                            Email.scheduled_date >= since,
                            Email.to_address == to,)

        return query.count(limit=1) > 0

    @classmethod
    def send(self, emails):
        to_addresses = []
        for email in emails:
            if self.we_are_spamming(email):
                # Do not send
                # This user has already recieved very recent emails

                # Debugging info
                logging.error("We are spamming {}:\n{}"
                              .format(email.to_address, email.to_dict()))
            elif email.to_address in to_addresses:
                # Do not send
                # We don't send multiple emails to an address per 'send'

                # Debugging info
                logging.error("We are spamming {}:\n{}"
                              .format(email.to_address, email.to_dict()))
            else:
                # Not spam! Let's send it
                to_addresses.append(email.to_address)

                # Debugging info
                logging.info(u"sending email: {}".format(email.to_dict()))
                logging.info(u"to: {}".format(email.to_address))
                logging.info(u"subject: {}".format(email.subject))

                if email.body:
                    logging.info(u"body:\n{}".format(email.body))
                    mandrill.send(to_address=email.to_address,
                                  subject=email.subject,
                                  body=email.body,
                                  template_data=email.template_data,
                                  )

                elif email.template:
                    logging.info(u"template: {}".format(email.template))
                    mandrill.send(to_address=email.to_address,
                                  subject=email.subject,
                                  template=email.template,
                                  template_data=email.template_data,
                                  )

                email.was_sent = True
                logging.info("""Sent successfully!""")

            # Note that we are attempting to send so that we don't keep attempting.
            email.was_attempted = True
            email.put()

    @classmethod
    def fetch_pending_emails(self):
        to_send = Email.query(
            Email.deleted == False,
            Email.scheduled_date <= datetime.datetime.utcnow(),
            Email.was_sent == False,
            Email.was_attempted == False,
        )

        return to_send.fetch()

    @classmethod
    def send_pending_email(self):
        """Send the next unsent emails in the queue.
        """

        emails = self.fetch_pending_emails()

        if emails:
            self.send(emails)
            return emails
        else:
            return None
