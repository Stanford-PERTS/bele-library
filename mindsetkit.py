from google.appengine.api import users
from google.appengine.api import users as app_engine_users
from google.appengine.ext import ndb
from google.appengine.ext import blobstore
from google.appengine.ext.webapp.util import run_wsgi_app
from webapp2_extras import security
from webapp2_extras import routes
from webapp2_extras.routes import RedirectRoute

import google.appengine.api.app_identity as app_identity
import cgi
import jinja2
import json
import logging
import os
import random
# Debugging. To use, start sdk via shell and add `pdb.set_trace()` to code.
import pdb
import re
import traceback
import urllib
import webapp2
import webapp2_extras.appengine.auth.models

from api import Api, PermissionDenied
from base_handler import BaseHandler
from model import User, Practice, Book, Chapter, Page, Theme, Topic, Lesson, ResetPasswordToken, AcceptAuthorshipToken
import config
import util
import view_counter
import mandrill
import locales


# Make sure this is off in production, it exposes exception messages.
debug = util.is_development()
def log(x):
    print 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX';
    print x
    return ''


class MetaView(type):
    """Allows code to be run before and after get and post methods.

    See: http://stackoverflow.com/questions/6780907/python-wrap-class-method
    """

    @staticmethod
    def wrap(method):
        """Return a wrapped instance method"""

        def outer(self, *args, **kwargs):

            ## BEFORE GET ##

            # Is the user returning from a google authentication page? If so,
            # examine the credentials in their cookie and attempt to log them
            # in.
            logging.info(u"MetaView Outer: ".format(self.request));

            if (self.request.get('google_login') == 'true'):

                if self.get_current_user():
                    # Don't try to log someone in if they already are, just
                    # clear the URL param.
                    refresh_url = util.set_query_parameters(
                        self.request.url,
                        google_login='',
                    )
                    self.redirect(refresh_url)
                else:
                    # This will set up a redirect, so make sure to return
                    # afterwards.
                    self.handle_google_response()
                return

            ## INHERITING GET HANDLER RUNS HERE ##

            return_value = method(self, *args, **kwargs)

            ## AFTER GET ##

            # nothing here... yet...

            return return_value

        return outer

    def __new__(cls, name, bases, attrs):
        """If the class has an http GET method, wrap it."""
        if 'get' in attrs:
            attrs['get'] = cls.wrap(attrs['get'])
        return super(MetaView, cls).__new__(cls, name, bases, attrs)


class ViewHandler(BaseHandler):
    """Superclass for page-generating handlers."""

    __metaclass__ = MetaView

    def get_jinja_environment(self, template_path='templates'):
        env = jinja2.Environment(
            autoescape=True,
            extensions=['jinja2.ext.autoescape'],
            loader=jinja2.FileSystemLoader(template_path),
        )
        env.filters['log'] = log
        return env

    def write(self, template_filename, template_path='templates', **kwargs):
        util.profiler.add_event("Begin ViewHandler:write")
        jinja_environment = self.get_jinja_environment(template_path)

        # Jinja environment filters:

        @jinja2.evalcontextfilter
        def jinja_json_filter(eval_context, value):
            """Seralize value as JSON and mark as safe for jinja."""
            return jinja2.Markup(json.dumps(value))

        jinja_environment.filters['to_json'] = jinja_json_filter

        def nl2br(value):
            """Replace new lines with <br> for html view"""
            return value.replace('\n', '<br>\n')

        jinja_environment.filters['nl2br'] = nl2br

        def format_datetime(value):
            # Formats datetime as Ex: "January 9, 2015"
            return '{dt:%B} {dt.day}, {dt.year}'.format(dt=value)

        jinja_environment.filters['datetime'] = format_datetime

        def format_ampescape(value):
            return value.replace('&', '%26')

        jinja_environment.filters['ampescape'] = format_ampescape

        def format_filetype(value):
            if value.split('/')[0] in ['application']:
                if value.split('/')[1] in ['pdf']:
                    formatted_type = 'pdf file'
                elif value.split('/')[1].find('wordprocessing') > -1:
                    formatted_type = 'word document'
                elif value.split('/')[1].find('presentation') > -1:
                    formatted_type = 'presentation'
                else:
                    formatted_type = 'document'
            elif value.split('/')[0] in ['image']:
                formatted_type = 'image file'
            else:
                formatted_type = value.split('/')[0]
            return formatted_type

        jinja_environment.filters['filetype'] = format_filetype

        util.profiler.add_event("Begin ViewHandler:add_jinja_filters")

        user = self.get_current_user()

        util.profiler.add_event("Begin ViewHandler:get_current_user()")

        # Only get sign in links if no user is present
        if user is None:
            # Sets up the google sign in link, used in modal on all pages,
            # which must include a special flag to alert this handler that
            # google credentials are present in the cookie. It should also
            # incorporate any redirect already set in the URL.
            redirect = str(self.request.get('redirect')) or self.request.url
            google_redirect = util.set_query_parameters(
                redirect, google_login='true')
            google_login_url = app_engine_users.create_login_url(google_redirect)
        else:
            google_login_url = ''

        util.profiler.add_event("Begin ViewHandler:get_login_redirects")

        # default parameters that all views get
        kwargs['user'] = user
        kwargs['google_login_url'] = google_login_url
        kwargs['hosting_domain'] = os.environ['HOSTING_DOMAIN']
        kwargs['share_url'] = self.request.url
        kwargs['google_client_id'] = config.google_client_id

        util.profiler.add_event("Begin ViewHandler:set_user_params")

        # Determine which Facebook app depending on environment
        kwargs['localhost'] = False
        if util.is_localhost():
            kwargs['localhost'] = True

        util.profiler.add_event("Begin ViewHandler:start_fetching_themes")

        # Fetch all themes and topics for navigation
        courses = self.api.get('Theme')
        if courses:
            # Fetch all topics for courses
            course_topic_ids = [id for course in courses for id in course.topics]
            course_topics = self.api.get_by_id(course_topic_ids)
            # Associate topics with appropriate courses
            for course in courses:
                course.associate_topics(course_topics)
                # Special case for "Teachers" kit
                if course.name == 'Growth Mindset for Teachers':
                    # IDK WHAT THIS IS
                    kwargs['teacher_topics'] = course.topics_list
        kwargs['courses'] = courses

        util.profiler.add_event("Begin ViewHandler:finish_fetching_themes")

        logging.info(util.profiler)

        # Try to load the requested template. If it doesn't exist, replace
        # it with a 404.
        try:
            template = jinja_environment.get_template(template_filename)
        except jinja2.exceptions.TemplateNotFound:
            logging.error("TemplateNotFound: {}".format(template_filename))
            return self.http_not_found()

        # logging.info('kwargs={}', kwargs['book'])

        # Render the template with data and write it to the HTTP response.
        self.response.write(template.render(kwargs))

    def handle_google_response(self):
        """Figure out the results of the user's interaction with google.

        Attempt to login a/o register, then refresh to clear temporary url
        parameters.
        """
        logging.info("Handling a google login response.")
        error_code = None
        response = self.authenticate('google')
        logging.info(u"Response is: {}".format(response))
        if isinstance(response, User):
            user = response
            logging.info(u"User {} found, logging them in.".format(user.email))
        elif (('email_exists' in response) or
              (response == 'credentials_missing')):
            # Provide the error code to the template so the UI can advise
            # the user.
            error_code = response
        elif response == 'credentials_invalid':
            logging.info("There's no record of this google user, registering.")
            response = self.register('google')
            if isinstance(response, User):
                user = response
                logging.info(u"Registered {}.".format(user.email))
            else:
                # This will get written into the template, and the UI can
                # display an appropriate message.
                error_code = response
                logging.info("Error in auto-registering google user.")
        # Now that google's response has been handled, refresh the
        # request. This will create one of two behaviors:
        # * If the user was correctly logged in a/o registered, they get
        #   the requested page, ready to use, no complications, no params.
        # * If there was an error, an error code is available about why,
        #   and the url fragment/hash will trigger the login modal so a
        #   message can be displayed.
        params = {'google_login': ''}  # means remove this parameter
        new_fragment = ''  # means remove hash/fragment
        if error_code:
            logging.info("Error code: {}.".format(error_code))
            params['google_login_error'] = error_code
            new_fragment = 'login'
        refresh_url = util.set_query_parameters(
            self.request.url, new_fragment=new_fragment, **params)
        self.redirect(refresh_url)

    def dispatch(self):
        try:
            logging.info("ViewHandler.dispatch()")
            # Call the overridden dispatch(), which has the effect of running
            # the get() or post() etc. of the inheriting class.
            BaseHandler.dispatch(self)

        except Exception as error:
            trace = traceback.format_exc()
            # We don't want to tell the public about our exception messages.
            # Just provide the exception type to the client, but log the full
            # details on the server.
            logging.error("{}\n{}".format(error, trace))
            response = {
                'success': False,
                'message': error.__class__.__name__,
            }
            if debug:
                self.response.write('<pre>{}</pre>'.format(
                    traceback.format_exc()))
            else:
                self.response.write("We are having technical difficulties.")
            return

    def http_not_found(self, **kwargs):
        """Respond with a 404.

        Example use:

        class Foo(ViewHandler):
            def get(self):
                return self.http_not_found()
        """
        # default parameters that all views get
        user = self.get_current_user()

        # Sets up the google sign in link, used in modal on all pages, which
        # must include a special flag to alert this handler that google
        # credentials are present in the cookie. It should also incorporate any
        # redirect already set in the URL.
        redirect = str(self.request.get('redirect')) or self.request.url
        google_redirect = util.set_query_parameters(
            redirect, google_login='true')
        google_login_url = app_engine_users.create_login_url(google_redirect)

        kwargs['user'] = user
        kwargs['google_login_url'] = google_login_url
        kwargs['hosting_domain'] = os.environ['HOSTING_DOMAIN']
        kwargs['share_url'] = self.request.url
        kwargs['google_client_id'] = config.google_client_id

        # Determine which Facebook app depending on environment
        kwargs['localhost'] = False
        if util.is_localhost():
            kwargs['localhost'] = True

        # Fetch all themes and topics for navigation
        courses = self.api.get('Theme')
        if courses:
            # fetch topics for each theme
            course_topic_ids = [id for course in courses for id in course.topics]
            course_topics = self.api.get_by_id(course_topic_ids)
            # associate topics with appropriate courses
            for course in courses:
                course.associate_topics(course_topics)
                # Special case for "Teachers" kit
                if course.name == 'Growth Mindset for Teachers':
                    kwargs['teacher_topics'] = course.topics_list
        kwargs['courses'] = courses

        self.error(404)
        jinja_environment = self.get_jinja_environment()
        template = jinja_environment.get_template('404.html')
        self.response.write(template.render(kwargs))

    def head(self, **kwargs):
        # You're not supposed to give a message body to HEAD calls
        # http://stackoverflow.com/questions/1501573/when-should-i-be-responding-to-http-head-requests-on-my-website
        self.response.clear()

    def options(self, **kwargs):
        # OPTION Response based on ->
        # http://zacstewart.com/2012/04/14/http-options-method.html
        self.response.set_status(200)
        self.response.headers['Allow'] = 'GET,HEAD,OPTIONS'


class Logout(ViewHandler):
    """Clears the user's session, closes connections to google."""
    def get(self):
        self.log_out()

        redirect = self.request.get('redirect') or '/'

        if util.is_localhost():
            # In the SDK, it makes sense to log the current user out of Google
            # entirely (otherwise admins have to click logout twice, b/c
            # existing code will attempt to sign them right in again).
            self.redirect(app_engine_users.create_logout_url(redirect))
        else:
            # In production, we don't want to sign users out of their Google
            # account entirely, because that would break their gmail, youtube,
            # etc. etc. Instead, just clear the cookies on *this* domain that
            # Google creates. That's what self.log_out() does above. So we're
            # done, except for a simple redirect.
            self.redirect(redirect)


class UnitTests(ViewHandler):
    def get(self):
        # @todo: read contents of unit test directory
        r = re.compile(r'^test_(\S+)\.py$')
        test_files = filter(lambda f: r.match(f), os.listdir('unit_testing'))
        test_suites = [r.match(f).group(1) for f in test_files]
        self.write('test.html', test_suites=test_suites)


class AboutPage(ViewHandler):

    def get(self):
        self.write(
            'about.html',
        )


class Admin(ViewHandler):

    def get(self):
        if self.get_current_user().is_admin:
            self.write(
                'admin.html',
            )
        else:
            self.redirect('/')


class LandingPage(ViewHandler):

    def get(self):
        books = (
            Book
            .query()
            .filter(Book.listed == True)
            .filter(Book.status == 'approved')
            .filter(Book.deleted == False)
            .order(-Book.display_order, -Book.votes_for)
            .fetch(10)
        )
        for book in books:
            if book.book_image:
                book.book_image = json.loads(book.book_image)['link']
            if book.icon:
                book.icon = json.loads(book.icon)['link']
            book.author_users = [
                user.to_client_dict() for user in User.get_by_id(book.authors)
            ]
        pages = (
            Page
            .query()
            .filter(Page.listed == True)
            .filter(Page.status == 'approved')
            .filter(Book.deleted == False)
            .order(-Page.display_order, -Page.votes_for)
            .fetch(5)
        )
        for page in pages:
            if page.iconPath:
                page.icon_thumbnail = page.iconPath + '?size=120'
            page.author_users = [
                user.to_client_dict() for user in User.get_by_id(page.authors)
            ]

        self.write(
            'main.html',
            featuredBooks=books,
            featuredPages=pages,
        )


class DiscoverPage(ViewHandler):

    def get(self):
        self.write(
            'discover.html',
        )


class UserPage(ViewHandler):

    def get(self, username=None):
        if username is None:
            if self.get_current_user():
                self.write(
                    'profile.html',
                    your_profile=True,
                    profile_user=self.get_current_user(),
                    profile_user_json=json.dumps(self.get_current_user().to_client_dict()),
                )
            else:
                self.redirect('/')
        else:
            users = self.api.get('User', canonical_username=username)
            if users:
                profile_user = users[0]
                your_profile = (profile_user is self.get_current_user())
                self.write(
                    'profile.html',
                    your_profile=your_profile,
                    profile_user=profile_user,
                    profile_user_json=json.dumps(profile_user.to_client_dict()),
                )
            else:
                return self.http_not_found()


class ResetPasswordPage(ViewHandler):

    def get(self, token):
        user = ResetPasswordToken.get_user_from_token_string(token)
        valid = user is not None
        self.write('reset_password.html', token=token, valid=valid)


class UnsubscribePage(ViewHandler):
    """Redirect page for email unsubscribe from Mandrill service"""

    def get(self):
        # Variables passed through to resubscribe button
        md_id = self.request.get('md_id')
        md_email = self.request.get('md_email')

        self.write(
            'unsubscribe.html',
            md_id=md_id,
            md_email=md_email,
        )


class ResubscribePage(ViewHandler):
    """Resubscribes a user to the email list

    Needs to be manually performed,
    So we ping Matt. Obviously."""

    def get(self):
        md_id = self.request.get('md_id')
        md_email = self.request.get('md_email')

        mandrill.send(
            to_address=config.from_server_email_address,
            subject="Please Re-subscribe!",
            body=(
                "&#128007; Heyo,<br><br>Someone requested they be "
                "re-subscribed to the MSK mailing list. We have to do this "
                "manually. Here's their info.<br><br><b>Email:</b> {}<br>"
                "<b>ID:</b> {}<br><br>Thanks!!"
                .format(md_email, md_id)
            ),
        )

        self.write(
            'resubscribe.html',
        )


class PracticeHomePage(ViewHandler):

    def get(self):
        self.redirect('/search', permanent=True)


class PageHomePage(ViewHandler):

    def get(self):
        self.redirect('/search', permanent=True)


class SearchPage(ViewHandler):

    def get(self):
        self.write(
            'search.html',
        )


class BelongingResources(ViewHandler):

    def get(self):
        self.redirect(
            '/search?tags=Belonging'
        )


class PageHandler(ViewHandler):

    def get(self, page_id):

        # Add info to dicts that assist templates with displaying correct UI elements.
        # Takes data param (page data) and a property_dict, the flat dictionary
        # that contains metadata for the content fields to display in this view.
        def process_property_dicts(data, property_dict):
            val = getattr(data, property_dict['data_prop'])
            if (val == property_dict['default_value']):
                property_dict['is_empty'] = True
                # set display value even though it will be hidden
                property_dict['display_value'] = property_dict['default_value']
            else:
                property_dict['is_empty'] = False
                has_suffix = property_dict['value_suffix'] is not None
                property_dict['display_value'] = u'{} {}'.format(val, property_dict['value_suffix']) if has_suffix else val

        id = Page.get_long_uid(page_id)
        page = self.api.get_by_id(id)
        authors = []

        if not page:
            # 404 if theme cannot be found
            return self.http_not_found()

        # These lists of dictionaries are used to store metadata about the
        # page's display fields.
        # - data_prop and scope_prop are used to help map angular values with
        #   their respective data values.
        # - value_suffix can be given a value to add a simple string to the end
        #   of the display value.
        # - Note: before being passed to the template, these dicts can/are
        #   expected to be further processed by adding data (such as the final
        #   display value)
        ui_props = page.ui_props.copy()
        first_section_keys = (
            'time_required',
            'required_materials',
            'preconditions_for_success',
            'advances_equity',
            'evidence_of_effectiveness',
        )
        first_section_props = [ui_props[k] for k in first_section_keys]
        second_section_keys = (
            'associated_measures',
            'acknowledgements',
            'preferred_citation',
        )
        second_section_props = [ui_props[k] for k in second_section_keys]

        # Increment view counts on the practice
        view_counter.increment(id)

        # TODO: Refactor this. Not sure what kind of author data we want to display/send to template yet.
        if page.authors:
            authors_data = User.get_by_id(page.authors)
            for a in authors_data:
                authors.append(a.to_client_dict())

        display_first_section_heading = False
        for property_dict in first_section_props:
            process_property_dicts(page, property_dict)
            if not property_dict['is_empty']:
                display_first_section_heading = True

        for property_dict in second_section_props:
            process_property_dicts(page, property_dict)

        relatedPages = []
        if len(page.related_pages) > 0:
            relatedPages = Page.get_by_id(page.related_pages)

        creator = authors[0]
        last_editor = User.get_by_id(page.last_edited_by) if page.last_edited_by else None
        user = self.get_current_user()
        is_author = user.uid in page.authors if user is not None else False
        additional_authors = authors[1:].remove(last_editor) if last_editor and last_editor in authors[1:] else authors[1:]

        self.write(
            'page.html',
            page=page,
            page_json=json.dumps(page.to_client_dict()),
            related_pages=relatedPages,
            authors=authors,
            authors_json=json.dumps(authors),
            first_author=creator,
            creator=creator,
            additional_authors=additional_authors,
            last_editor=last_editor,
            tags=page.tags,
            license=page.use_license,
            first_section_props=first_section_props,
            second_section_props=second_section_props,
            display_first_section_heading=display_first_section_heading,
            breadcrumb_title=None,
            is_author=is_author or (user and user.is_admin),
            is_admin=user and user.is_admin,
            entity_type='page',
        )


class PracticePage(ViewHandler):

    def get(self, practice_id):
        id = Practice.get_long_uid(practice_id)
        practice = self.api.get_by_id(id)
        if practice:
            # Increment view counts on the practice
            view_counter.increment(id)

            # Get related practices
            related_practices = Practice.get_related_practices(practice, 3)

            creator = practice.key.parent().get().to_client_dict()
            self.write(
                'practice.html',
                practice=practice,
                creator=creator,
                creator_json=json.dumps(creator),
                related_practices=related_practices,
            )
        else:
            # 404 if theme cannot be found
            return self.http_not_found()


class UploadPracticePage(ViewHandler):

    def get(self, practice_id=None):
        user = self.get_current_user()

        if user is None:
            self.redirect('/search')
            return

        # Check if user is practice creator or admin
        if not user.is_admin and practice_id:
            practice = self.api.get_by_id(Practice.get_long_uid(practice_id))
            creator = practice.key.parent().get()
            if creator is not user:
                self.redirect('/practices/{}'.format(practice_id))

        self.write(
            'practice-upload.html',
            practice_id=practice_id,
        )


class UploadPage(ViewHandler):

    def get(self, page_id=None):
        user = self.get_current_user()
        full_chapter_id = ""
        book_id = ""
        if user is None:
            self.redirect('/discover')
            return

        # Check if user is practice creator or admin

        page_json = "''";
        if page_id:
            page = self.api.get_by_id(Page.get_long_uid(page_id))
            pageDict = page.to_client_dict();
            if page.icon:
                icon_path = util.extract_value_from_json(page.icon, 'link')
                pageDict['iconPath'] = icon_path + '?size=360' if icon_path else icon_path
            page_json = json.dumps(pageDict)

        if not user.is_admin and page_id:
            if user.uid not in page.authors:
                self.redirect('/pages/{}'.format(page_id))

        chapter_id = self.request.get('chapter_id')
        if chapter_id:
            full_chapter_id = Chapter.get_long_uid(chapter_id)
            book_id = Chapter.get_by_id(full_chapter_id).books[0]

        self.write(
            'page-upload.html',
            page_id=page_id,
            page_json=page_json,
            chapter_id=full_chapter_id,
            book_id=book_id,
        )


class ManageBook(ViewHandler):

    def get(self, book_id=None):
        user = self.get_current_user()
        expand = '';
        if user is None:
            self.redirect('/books/{}'.format(book_id))
            return


        if book_id is not None:
            book_id = Book.get_long_uid(book_id)
            book = self.api.get_by_id(book_id)

            if not user.is_admin and user.uid not in book.authors:
                self.redirect('/books/{}'.format(book_id))

            book.book_image = util.extract_value_from_json(book.book_image, 'link')
            icon_link = util.extract_value_from_json(book.icon, 'link')
            book.icon = icon_link + '?size=360' if icon_link else icon_link;
            book_json = json.dumps(book.to_client_dict())

        expand = Chapter.get_long_uid(self.request.get('expand'))

        self.write(
            'book-manage.html',
            book=book.to_client_dict(),
            book_json=book_json,
            expand=expand,
        )


class BookHandler(ViewHandler):

    def get(self, book_id):
        user = self.get_current_user()
        section_props = [
            {
                'default_value': '',
                'data_prop': 'acknowledgements',
                'scope_prop': 'pageAcknowledgements',
                'heading_title': 'Acknowledgements',
                'value_suffix': None,
              },
              {
                'default_value': '',
                'data_prop': 'preferred_citation',
                'scope_prop': 'pageCitations',
                'heading_title': 'Preferred Citation',
                'value_suffix': None,
              }
            ]
        id = Book.get_long_uid(book_id)
        book = self.api.get_by_id(id)
        first_chapter_link = ''
        first_page_link = ''
        authors=[]
        if book is not None:
            if book.authors:
                authors_data = User.get_by_id(book.authors)
                for a in authors_data:
                    authors.append(a.to_client_dict())
            chapter_page_data = book.get_chapters_with_pages()
            pages_count = 0;
            if book.chapters:
                for chapter in chapter_page_data:
                    pages_count += len(chapter['pages'])
                    # Only pass page data if they are an author
                    chapter_pages = []
                    for chapter_page in chapter['pages']:
                        if chapter_page['status'] == 'approved':
                            chapter_pages.append(chapter_page)
                        elif user and (user.is_admin or user.uid in chapter_page['authors']):
                            chapter_pages.append(chapter_page)
                    chapter.pages = chapter_pages
                first_page_link = '/books/{}'.format(book.short_uid)
                has_first_page = chapter_page_data and chapter_page_data[0] and chapter_page_data[0]['pages']
                book.page_count = pages_count;
                if has_first_page:
                    first_page_link = '/{}/{}/{}'.format(
                        first_page_link,
                        chapter_page_data[0]['short_uid'],
                        chapter_page_data[0]['pages'][0]['short_uid'])
            for file_prop in Book.file_props:
                json_file = getattr(book, file_prop)
                setattr(book, file_prop, util.extract_value_from_json(json_file, 'link'))

            book.color = '#58b070'; #TODO
            book.target_audience = 'TODO';
            book.estimated_duration = 9999; #TODO: should you just sum pages durations? Any default value?

            # Get translated text and locale
            if book.locale in config.available_locales:
                locale = book.locale
            else:
                locale = default_locale

            locale = 'en'

            creator = authors[0]
            last_editor = User.get_by_id(book.last_edited_by) if book.last_edited_by else None
            user = self.get_current_user()
            is_author = user.uid in book.authors if user is not None else False
            additional_authors = authors[1:].remove(last_editor) if last_editor and last_editor in authors[1:] else authors[1:]


            self.write(
                'book-page.html',
                book=book,
                first_page_link=first_page_link,
                locale=locale,
                translation=locales.translations[locale]["books"],
                chapters_json=json.dumps(book.chapters),
                chapter_page_data=chapter_page_data,
                chapter_page_data_json=json.dumps(chapter_page_data),
                section_props=section_props,
                last_editor=last_editor,
                creator=creator,
                additional_authors=additional_authors,
                is_author=is_author or (user and user.is_admin),
                is_admin=user and user.is_admin,
                entity_type='book',
            )
        else:
            return self.http_not_found()

    def head(self, book_id):
        # Include an override here to not confuse bad subdirectories as 200 OK
        id = Book.get_long_uid(book_id)
        book = self.api.get_by_id(id)
        if book is not None:
            self.response.clear()
        else:
            self.error(404)

    def options(self, book_id):
        # Include an override here to not confuse bad subdirectories as 200 OK
        id = Book.get_long_uid(book_id)
        book = self.api.get_by_id(id)
        if book is not None:
            self.response.set_status(200)
            self.response.headers['Allow'] = 'GET,HEAD,OPTIONS'
        else:
            self.error(404)


class BookChapterHandler(ViewHandler):
    """Redirects book chapters to book page with # navigation"""

    def get(self, book_id, chapter_id):
        # Redirects now to theme.
        self.redirect('/books/{}#{}'.format(book_id, chapter_id), permanent=True)


class BookPageHandler(ViewHandler):
    """Renders a page with added chapter and book navigation UI"""

    def get(self, book_id, chapter_id, page_id):
        # Add info to dicts that assist templates with displaying correct UI elements.
        # Takes data param (page data) and a property_dict, the flat dictionary
        # that contains metadata for the content fields to display in this view.
        def process_property_dicts(data, property_dict):
            val = getattr(data, property_dict['data_prop'])
            if (val == property_dict['default_value']):
                property_dict['is_empty'] = True
                # set display value even though it will be hidden
                property_dict['display_value'] = property_dict['default_value']
            else:
                property_dict['is_empty'] = False
                has_suffix = property_dict['value_suffix'] is not None
                property_dict['display_value'] = '{} {}'.format(val, property_dict['value_suffix']) if has_suffix else val

        id = Page.get_long_uid(page_id)
        page = self.api.get_by_id(id)
        authors = []
        if page:
            # These lists of dictionaries are used to store metadata about the
            # page's display fields.
            # - data_prop and scope_prop are used to help map angular values with
            #   their respective data values.
            # - value_suffix can be given a value to add a simple string to the end
            #   of the display value.
            # - Note: before being passed to the template, these dicts can/are
            #   expected to be further processed by adding data (such as the final
            #   display value)
            ui_props = page.ui_props.copy()
            first_section_keys = (
                'time_required',
                'required_materials',
                'preconditions_for_success',
                'advances_equity',
                'evidence_of_effectiveness',
            )
            first_section_props = [ui_props[k] for k in first_section_keys]
            second_section_keys = (
                'associated_measures',
                'acknowledgements',
                'preferred_citation',
            )
            second_section_props = [ui_props[k] for k in second_section_keys]

            # Increment view counts on the practice
            view_counter.increment(id)

            # TODO: Refactor this. Not sure what kind of author data we want to display/send to template yet.
            if page.authors:
                authors_data = User.get_by_id(page.authors)
                for a in authors_data:
                    authors.append(a.to_client_dict())

            display_first_section_heading = False
            for property_dict in first_section_props:
                process_property_dicts(page, property_dict)
                if not property_dict['is_empty']:
                    display_first_section_heading = True

            for property_dict in second_section_props:
                process_property_dicts(page, property_dict)

            last_editor = User.get_by_id(page.last_edited_by) if page.last_edited_by else None
            user = self.get_current_user()
            is_author = user.uid in page.authors if user is not None else False

        full_book_id = Book.get_long_uid(book_id)
        book = self.api.get_by_id(full_book_id)

        full_chapter_id = Chapter.get_long_uid(chapter_id)
        chapter = self.api.get_by_id(full_chapter_id)

        full_page_id = Page.get_long_uid(page_id)
        page = self.api.get_by_id(full_page_id)

        creator = authors[0]
        last_editor = User.get_by_id(page.last_edited_by) if page.last_edited_by else None
        user = self.get_current_user()
        is_author = user.uid in page.authors if user is not None else False
        additional_authors = authors[1:].remove(last_editor) if last_editor and last_editor in authors[1:] else authors[1:]
        breadcrumb_title = book.title + ' / ' +  chapter.title

        # check all content objects were found
        if page is None or chapter is None or book is None:
            return self.http_not_found()

        # Increment view counts on the page
        view_counter.increment(full_page_id)
        view_counter.increment('{}:{}:{}'.format(
            full_book_id, full_chapter_id, full_page_id))

        authors=[]
        if page.authors:
            authors_data = User.get_by_id(page.authors)
            for a in authors_data:
                authors.append(a.to_client_dict())

        # Get other chapters in book for navigating
        chapters = []
        if book.chapters:
            chapters = self.api.get_by_id(book.chapters)

        # get other pages in chapter for navigating
        pages = []
        # first check for bad chapter--page match
        if chapter.pages:
            pages = self.api.get_by_id(chapter.pages)

            # get chapter index and previous and next lessons
            page_index = 0
            chapter_index = 0
            if chapter.uid in book.chapters:
                chapter_index = book.chapters.index(chapter.uid)
            if page.uid in chapter.pages:
                page_index = chapter.pages.index(page.uid)

            # get next chapter from current or next topic
            next_page = ''
            next_page_url = ''
            next_chapter = ''
            next_chapter_url = ''
            next_url = ''
            if page_index < len(pages) - 1:
                next_page = pages[page_index + 1]
                next_page_url = '/books/{}/{}/{}'.format(
                    book.short_uid, chapter.short_uid, next_page.short_uid)
                next_url = next_page_url
            elif chapter_index < len(book.chapters) - 1:
                next_chapter = chapters[chapter_index + 1]
                next_chapter_url = '/books/{}/{}'.format(
                    book.short_uid, next_chapter.short_uid)
                next_url = next_chapter_url

        # Get translated text and locale
        if book.locale in config.available_locales:
            locale = book.locale
        else:
            locale = config.default_locale

        color='#58b070' #TODO

        self.write(
            '/page.html'.format(page.short_uid),
            book=book,
            chapter=chapter,
            page=page,
            pages=pages,
            page_index=page_index,
            next_page=next_page,
            next_page_url=next_page_url,
            next_chapter=next_chapter,
            next_chapter_url=next_chapter_url,
            next_url=next_url,
            color=color,
            audience='',
            locale=locale,
            translation=locales.translations[locale]["pages"],
            creator=creator,
            last_editor=last_editor,
            tags=page.tags,
            license=page.use_license,
            first_section_props=first_section_props,
            second_section_props=second_section_props,
            display_first_section_heading=display_first_section_heading,
            breadcrumb_title=breadcrumb_title,
            is_author=is_author or (user and user.is_admin),
            is_admin=user and user.is_admin,
            additional_authors=additional_authors,
            entity_type='page',
        )


class PageAuthorshipHandler(ViewHandler):
    """Redirects book chapters to book page with # navigation"""
    def get(self, page_id):
        uid = self.request.get('uid')
        token = self.request.get('token')
        user = AcceptAuthorshipToken.get_user_from_token_string(token)
        valid = user is not None
        if page_id is not None:
            page_id = Page.get_long_uid(page_id)
            page = self.api.get_by_id(page_id)
            authors = page.authors
            # Add to authors if token is valid
            if valid and uid not in authors:
                authors.append(uid)
                page.authors = authors
                page.put()
                AcceptAuthorshipToken.delete(token)
                self.redirect('/pages/{}'.format(page_id), permanent=True)
            else:
                self.write('404.html', message='invalid token')
                # self.response.write(json.dumps(
                #     {'error': True, 'message': 'invalid token'}))
        else:
            self.response.write(json.dumps(
                {'error': True, 'message': 'invalid parameters'}))


class BookAuthorshipHandler(ViewHandler):
    """Redirects book chapters to book page with # navigation"""
    def get(self, book_id):
        uid = self.request.get('uid')
        token = self.request.get('token')
        user = AcceptAuthorshipToken.get_user_from_token_string(token)
        valid = user is not None
        logging.info('book_id={}, uid={}, token={}, user={}'.format(book_id, uid, token, user))
        if book_id is not None:
            book_id = Book.get_long_uid(book_id)
            book = self.api.get_by_id(book_id)
            authors = book.authors
            # Add to authors if token is valid
            if valid and uid not in authors:
                authors.append(uid)
                book.authors = authors
                book.put()
                AcceptAuthorshipToken.delete(token)
                self.redirect('/books/{}'.format(book_id), permanent=True)
            else:
                self.write('404.html', message='invalid token')
                # self.response.write(json.dumps(
                #     {'error': True, 'message': 'invalid token'}))
        else:
            self.response.write(json.dumps(
                {'error': True, 'message': 'invalid parameters'}))


webapp2_config = {
    'webapp2_extras.sessions': {
        # Related to cookie security, see:
        # http://webapp-improved.appspot.com/api/webapp2_extras/sessions.html
        'secret_key': config.session_cookie_secret_key,
    },
}


class MSKRoute(RedirectRoute):
    """Route subclass that defaults to strict_slash=True
    to automatically redirect urls ending with '/'
    to their equivalent without

    https://webapp-improved.appspot.com/api/webapp2_extras/routes.html
    """
    def __init__(self, template, handler, strict_slash=True, name=None,
                 **kwargs):

        # Routes with 'strict_slash=True' must have a name
        if strict_slash and name is None:
            # Set a name from the template
            # ** Be sure this isn't creating duplicate errors
            # ** but 'template' should be unique so I think it's good.
            name = template

        return super(MSKRoute, self).__init__(
            template, handler=handler, strict_slash=strict_slash, name=name,
            **kwargs
        )


application = webapp2.WSGIApplication([
    MSKRoute('/logout', Logout),
    MSKRoute('/admin/test', UnitTests),
    MSKRoute('/about', AboutPage),
    MSKRoute('/manage', Admin),
    MSKRoute('/', LandingPage),
    MSKRoute('/profile', UserPage),
    MSKRoute('/users/<username>', UserPage),
    MSKRoute('/reset_password/<token>', ResetPasswordPage),
    MSKRoute('/unsubscribe', UnsubscribePage),
    MSKRoute('/resubscribe', ResubscribePage),
    MSKRoute('/practices', PracticeHomePage),
    MSKRoute('/search', SearchPage),
    MSKRoute('/discover', DiscoverPage),
    MSKRoute('/books/manage/<book_id>', ManageBook),
    MSKRoute('/books/<book_id>', BookHandler),
    MSKRoute('/pages/upload', UploadPage),
    MSKRoute('/pages/edit/<page_id>', UploadPage),
    MSKRoute('/pages', PageHomePage),
    MSKRoute('/pages/<page_id>', PageHandler),
    MSKRoute('/pages/<page_id>/accept_authorship', PageAuthorshipHandler),
    MSKRoute('/books/<book_id>/accept_authorship', BookAuthorshipHandler),
    MSKRoute('/books/<book_id>/<chapter_id>/<page_id>', BookPageHandler),
    MSKRoute('/books/<book_id>/<chapter_id>', BookChapterHandler),
    #TODO: remove practice routes
    MSKRoute('/practices/upload', UploadPracticePage),
    MSKRoute('/practices/edit/<practice_id>', UploadPracticePage),
    MSKRoute('/practices/<practice_id>', PracticePage),
], config=webapp2_config, debug=True)
