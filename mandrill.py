from google.appengine.api import urlfetch
from google.appengine.ext import ndb
import json
import jinja2

import config
import util
import logging


# Setup jinja2 environment using the email subdirectory in templates
JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader('templates/emails'),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


def send(template_data={}, **kwargs):
    # Determine if message should send
    if util.is_development() and not config.should_deliver_smtp_dev:
        logging.info('\n\n---------------------------------------------------')
        logging.info('Email not sent, config.should_deliver_smtp_dev False.')
        logging.info('Email params:')
        logging.info(kwargs)
        logging.info(template_data)
        if kwargs['template'] == 'authorship_email.html':
            logging.info(
                '/{entity_type}/{entity_id}/accept_authorship?uid={to_uid}&token={token}'
                .format(**template_data)
            )
        logging.info('\n---------------------------------------------------\n')
        return

    subject = render(kwargs['subject'], **template_data)

    # Determine if using html string or a template
    body = ''
    if 'body' in kwargs:
        body = render(kwargs['body'], **template_data)
    elif 'template' in kwargs:
        body = render_template(kwargs['template'], **template_data)

    # JSON for Mandrill HTTP POST request
    sv = ndb.Key('SecretValue', 'mandrill_api_key').get()
    api_key = getattr(sv, 'value', config.mandrill_api_key)
    if not util.is_development() and api_key is config.mandrill_api_key:
        logging.error("No mandrill api_key set in production!")
    json_mandrill = {
        "key": api_key,
        "message": {
            "html": body,
            "subject": subject,
            "from_email": config.from_server_email_address,
            "from_name": "BELE Library",
            "inline_css": True,
            "to": format_to_address(kwargs['to_address'])
        }
    }

    # URL for Mandrill HTTP POST request
    url = "https://mandrillapp.com/api/1.0/messages/send.json"
    rpc = urlfetch.create_rpc()
    urlfetch.make_fetch_call(rpc, url=url,
        payload=json.dumps(json_mandrill),
        method=urlfetch.POST,
        headers={'Content-Type': 'application/x-www-form-urlencoded'})
    try:
        result = rpc.get_result()
        logging.info(u"...{}".format(result.status_code))
        logging.info(result.content)
        if result.status_code == 200:
            text = result.content
    except urlfetch.DownloadError:
        # Request timed out or failed.
        logging.error('Email failed to send.')
        result = None
    return result


# Formats the "to" field to fit conventions
def format_to_address(unformatted_to):
    formatted_to = []
    # Handles list of strings or single string
    for email in unformatted_to if not isinstance(unformatted_to, basestring) else [unformatted_to]:
        formatted_to.append({
            "email": email,
            "type": "to"
        })
    return formatted_to


# Creates email html from a string using jinja2
def render(s, **template_data):
    return jinja2.Environment().from_string(s).render(**template_data)


# Loads email html from a template using jinja2
def render_template(template, **template_data):
    return JINJA_ENVIRONMENT.get_template(template).render(**template_data)