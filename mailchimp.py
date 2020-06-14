"""Mailchimp API handlers for list management
"""

from google.appengine.api import urlfetch
import json
import jinja2
import config
import util
import logging
import base64
import hashlib

# http://kb.mailchimp.com/api/article/how-to-manage-subscribers

API_ROOT = 'https://' + config.mailchimp_dc + '.api.mailchimp.com/3.0/'


def subscribe(email, **kwargs):
    """Subscribes a new user to the list
    """

    merge_fields = {}

    # Look for additional information (apart from email)
    first_name = ''
    last_name = ''
    if 'first_name' in kwargs:
        merge_fields['FNAME'] = kwargs['first_name']
    if 'last_name' in kwargs and kwargs['last_name']:
        merge_fields['LNAME'] = kwargs['last_name']

    json_payload = {
        "email_address": email.lower(),
        "status": "subscribed",
        "merge_fields": merge_fields
    }
    headers = {
        "Authorization": "Basic %s" % base64.b64encode("username:" + config.mailchimp_api_key),
        "Content-Type": "application/x-www-form-urlencoded"
    }
    url = API_ROOT + 'lists/' + config.mailchimp_list_id + '/members'
    rpc = urlfetch.create_rpc()
    urlfetch.make_fetch_call(
        rpc, url=url,
        payload=json.dumps(json_payload),
        method=urlfetch.POST,
        headers=headers)
    try:
        result = rpc.get_result()
        if result.status_code == 400:
            logging.warning(result.content)
            result = None
        elif result.status_code == 200:
            logging.info(u'User subscribed to Mailchimp: {}'.format(email))
    except urlfetch.DownloadError:
        # Request timed out or failed. This generally doesn't actually indicate
        # a problem, however, as we've checked that these users are actually
        # added to the mailchimp list. So just a warning.
        logging.warning('Mailchimp list subscription failed.')
        result = None
    return result


def unsubscribe(email):
    """Unsubscribes an existing user from the list
    """
    json_payload = {
        "status": "unsubscribed"
    }
    headers = {
        "Authorization": "Basic %s" % base64.b64encode("username:" + config.mailchimp_api_key),
        "Content-Type": "application/x-www-form-urlencoded"
    }
    # Subscribers are stored as endpoints using MD5 hashing on lowercase emails
    formatted_email = email.lower()
    member_code = hashlib.md5(formatted_email).hexdigest()

    url = API_ROOT + 'lists/' + config.mailchimp_list_id + '/members/' + member_code
    rpc = urlfetch.create_rpc()
    urlfetch.make_fetch_call(
        rpc, url=url,
        payload=json.dumps(json_payload),
        method=urlfetch.PATCH,
        headers=headers)
    try:
        result = rpc.get_result()
        if result.status_code == 400:
            logging.warning(result.content)
        elif result.status_code == 200:
            logging.info(u'User unsubscribed to Mailchimp: {}'.format(email))
    except urlfetch.DownloadError:
        # Request timed out or failed.
        logging.error('Mailchimp list unsubscribe failed.')
        result = None
    return result


def resubscribe(email):
    """Resubscribes an unsubscribed email
    If email was never subscribed, returns None
    """
    json_payload = {
        "status": "subscribed"
    }
    headers = {
        "Authorization": "Basic %s" % base64.b64encode("username:" + config.mailchimp_api_key),
        "Content-Type": "application/x-www-form-urlencoded"
    }
    # Subscribers are stored as endpoints using MD5 hashing on lowercase emails
    formatted_email = email.lower()
    member_code = hashlib.md5(formatted_email).hexdigest()

    url = API_ROOT + 'lists/' + config.mailchimp_list_id + '/members/' + member_code
    rpc = urlfetch.create_rpc()
    urlfetch.make_fetch_call(
        rpc, url=url,
        payload=json.dumps(json_payload),
        method=urlfetch.PATCH,
        headers=headers)
    try:
        result = rpc.get_result()
        if result.status_code == 400:
            logging.warning(result.content)
        elif result.status_code == 404:
            # Not found, need to subscribe
            result = None
        elif result.status_code == 200:
            logging.info(u'User resubscribed to Mailchimp: {}'.format(email))
    except urlfetch.DownloadError:
        # Request timed out or failed.
        logging.error('Mailchimp list resubscribe failed.')
        result = None
    return result
