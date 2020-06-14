"""Collection of hard-coded settings."""

unit_test_directory = 'unit_testing'

session_cookie_name = 'bele-library_login'
session_cookie_secret_key = ''

# Auth types
# * own - For those who sign in by typing in their email address and
#     password. They have a password hash. Their auth_ids look like
#     ''
# * google - For those who sign in via google. They don't have a password
#     hash; google just tells us they're legit. Their auth_ids look like
#     'google:1234567890', where the numbers are their google identifier.

auth_types = ['own', 'google']

non_admins_can_create = ['Practice', 'Book', 'Chapter', 'Page', 'Comment', 'Feedback', 'Vote']

public_can_create = ['Feedback']

created_as_children = ['Practice', 'Comment', 'Vote']

created_with_author = ['Book', 'Page']

# Types of models indexed for search
indexed_models = ['Book', 'Page']

allowed_relationships = {
    ('Theme', 'Topic'): {'child_list': 'topics',
                         'parent_list': 'themes'},
    ('Topic', 'Lesson'): {'child_list': 'lessons',
                          'parent_list': 'topics'},
    ('Theme', 'Lesson'): {'child_list': 'popular_lessons',
                          'parent_list': 'popular_in'},
    ('Book', 'Chapter'): {'child_list': 'chapters',
                         'parent_list': 'books'},
    ('Chapter', 'Page'): {'child_list': 'pages',
                         'parent_list': 'chapters'},
}

# Locales available
available_locales = ['en', 'es']
default_locale = 'en'

# The name of the full text search index that we maintain for content entities.
content_index = 'content_2019_001'

# The name of the full text search index that we maintain for user entities.
user_index = 'user_2019_001'

# at least 8 characters, ascii only
# http://stackoverflow.com/questions/5185326/java-script-regular-expression-for-detecting-non-ascii-characters
password_pattern = r'^[\040-\176]{8,}$'

# Google sign in
google_client_id = 'XXXXX.apps.googleusercontent.com'
google_client_secret = 'XXXXX'

# Mandrill SMTP API Key
mandrill_api_key = ''

# Mailchimp API Key
mailchimp_api_key = ''
mailchimp_dc = ''
# Mailchimp List number
mailchimp_list_id = ''

# We want the entity store to ignore these properties, mostly because they
# can change in ways it doesn't expect, and it shouldn't be writing to them
# anyway. These properties will be prefixed with an underscore before being
# sent to the client.
client_private_properties = [
    'modified',
    'auth_id',
]

# These properties should never be exposed to the client.
client_hidden_properties = [
    'hashed_password',
]

boolean_url_arguments = [
    'listed',
    'pending',
    'vote_for',
    'promoted',
]

integer_url_arguments = [
    'votes_for',
    'votes_against',
    'estimated_duration',
    'lesson_count',
    'min_grade',
    'max_grade',
]

# UTC timezone, in ISO date format: YYYY-MM-DD
date_url_arguments = [
    'scheduled_date',  # used in sending emails
]

# UTC timezone, in an ISO-like format (missing the 'T' character between
# date and time): YYYY-MM-DD HH:mm:SS
datetime_url_arguments = [
]

# Converted to JSON with json.dumps().
json_url_arguments = [
    'json_properties',
    'template_data',
]

list_url_arguments = [
    'tags',
    'subjects',
]

# JSON only allows strings as dictionary keys. But for these values, we want
# to interpret the keys as numbers (ints).
json_url_arguments_with_numeric_keys = [
]

# These arguments are meta-data and are never applicable to specific entities
# or api actions. They appear in url_handlers.BaseHandler.get().
ignored_url_arguments = [
    'escape_impersonation',
    'impersonate,'
]

# also, any normal url argument suffixed with _json will be interpreted as json

# Converted by util.get_request_dictionary()
# Problem: we want to be able to set null values to the server, but
# angular drops these from request strings. E.g. given {a: 1, b: null}
# angular creates the request string '?a=1'
# Solution: translate javascript nulls to a special string, which
# the server will again translate to python None. We use '__null__'
# because is more client-side-ish, given that js and JSON have a null
# value.
# javascript | request string | server
# -----------|----------------|----------
# p = null;  | ?p=__null__    | p = None
url_values = {
    '__null__': None,
}

# In URL query strings, only the string 'true' ever counts as boolean True.
true_strings = ['true']


# Email settings
#
# Platform generated emails can only be sent from email addresses that have
# viewer permissions or greater on app engine.  So if you are going to change
# this please add the sender as an application viewer on
# https://appengine.google.com/permissions?app_id=s~pegasusplatform
#
# There are other email options if this doesn't suit your needs check the
# google docs.
# https://developers.google.com/appengine/docs/python/mail/sendingmail

from_server_email_address = ""

# This address should forward to the development team
to_dev_team_email_address = ""

# These people want to know about pratice uploads so they can manage/approve
# content.
page_upload_recipients = [
    '',
]

# These people want to know about pratice uploads so they can manage/approve
# content.
practice_upload_recipients = [
    '',
]

# These people want to know about feedback so they can reply if needed.
feedback_recipients = [
    '',
]

# These people want to know about feedback so they can reply if needed.
comment_recipients = [
    '',
]

# if we exceed this for a given to address, an error will be logged
suggested_delay_between_emails = 10  # minutes

# spam whitelist
addresses_we_can_spam = [
    to_dev_team_email_address,
    from_server_email_address,
]

# Determines if Mandrill sends emails on local or dev environments
should_deliver_smtp_dev = False


# Redirection mapping
# @todo: Remove all of these redirects by 2018
#
# These dictionaries are used to maintain SEO 'juice' on old routes
# that are no longer active.
# See 'mindsetkit.py' for implementation

# List of special redirections for removed or relocated topics
# Format: '<topic.short_uid>': 'new route'
topic_redirection_map = {}

# List of special redirections for removed or relocated 'topic/lesson's
# Format: '<topic.short_uid>/<lesson.short_uid>': 'new route'
lesson_redirection_map = {}

# List of special redirections for the update Spanish parent's course
# Format: '<topic.short_uid>/<lesson.short_uid>':
#             '<new-topic.short_uid>/<new-lesson.short_uid>'
# Course short_uid is handled automatically
spanish_redirection_map = {}