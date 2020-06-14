w"""
Email Model
===========

Deprecated?
"""

from google.appengine.api import mail
import datetime
import jinja2
import logging
import markdown

import config
import util
import searchable_properties as sndb

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
    from_address = sndb.StringProperty(required=True)
    reply_to = sndb.StringProperty(default=config.from_server_email_address)
    subject = sndb.StringProperty(default="A message from the Mindset Kit")
    body = sndb.TextProperty()
    html = sndb.TextProperty()
    scheduled_date = sndb.DateProperty()
    was_sent = sndb.BooleanProperty(default=False)
    was_attempted = sndb.BooleanProperty(default=False)
    errors = sndb.TextProperty()

    @classmethod
    def create(klass, template_data={}, **kwargs):
        def render(s):
            return jinja2.Environment().from_string(s).render(**template_data)

        kwargs['subject'] = render(kwargs['subject'])
        kwargs['body'] = render(kwargs['body'])

        return super(klass, klass).create(**kwargs)

    @classmethod
    def we_are_spamming(self, email):
        """Did we recently send email to this recipient?"""

        to = email.to_address

        # We can spam admins, like 
        # so we white list them in the config file
        if to in config.addresses_we_can_spam:
            return False

        # We can also spam admins living at a @mindsetkit.org
        if to.endswith('mindsetkit.org'):
            return False

        # Temporary spamming override...
        return False

        since = datetime.datetime.utcnow() - datetime.timedelta(
            days=config.suggested_delay_between_emails)

        query = Email.query(Email.was_sent == True,
                            Email.scheduled_date >= since)

        return query.count(limit=1) > 0

    @classmethod
    def send(self, email):
        if self.we_are_spamming(email):
            logging.error("We are spamming {}:\n{}"
                          .format(email.to_address, email.to_dict()))

        # Note that we are attempting to send so that we don't keep attempting.
        email.was_attempted = True
        email.put()

        # Debugging info
        logging.info(u"sending email: {}".format(email.to_dict()))
        logging.info(u"to: {}".format(email.to_address))
        logging.info(u"subject: {}".format(email.subject))
        logging.info(u"body:\n{}".format(email.body))

        # Make html version if it has not been explicitly passed in.
        if not email.html:
            email.html = (
                jinja2.Environment(loader=jinja2.FileSystemLoader('templates'))
                .get_template('email.html')
                .render({'email_body': markdown.markdown(email.body)})
            )

        # Try to email through App Engine's API.
        mail.send_mail(email.from_address,
                       email.to_address,
                       email.subject,
                       email.body,
                       reply_to=email.reply_to,
                       html=email.html)

        email.was_sent = True
        logging.info("""Sent successfully!""")
        email.put()

    @classmethod
    def fetch_next_pending_email(self):
        to_send = Email.query(
            Email.deleted == False,
            Email.scheduled_date <= datetime.datetime.utcnow(),
            Email.was_sent == False,
            Email.was_attempted == False,
        )

        return to_send.get()

    @classmethod
    def send_pending_email(self):
        """Send the next unsent email in the queue.

        We only send one email at a time; this allows us to raise errors for
        each email and avoid sending some crazy huge mass mail.
        """

        email = self.fetch_next_pending_email()

        if email:
            self.send(email)
            return email
        else:
            return None