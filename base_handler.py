from google.appengine.api import users as app_engine_users
from pyfb import Pyfb as Facebook
from webapp2_extras import sessions
import logging
import webapp2

from api import Api, PermissionDenied
from model import User, DuplicateUser, Email
from passlib.hash import sha256_crypt
import config
import datetime
import os
import util
import mandrill


class BaseHandler(webapp2.RequestHandler):
    """Ancestor of all other views/handlers."""
    def dispatch(self):
        """Wraps the other request handlers.

        * Manages sessions
        * Manages request profiling
        """
        # ** Code to run before all handlers goes here. ** #

        # Mark the start time of the request. You can add events to this
        # profiler in any request handler like this:
        # util.profiler.add_event("this is my event")
        util.profiler.clear()
        util.profiler.add_event('START')

        # Get a session store for this request.
        self.session_store = sessions.get_store(request=self.request)

        if (False and app_engine_users.is_current_user_admin() and
            not self.get_current_user() and
                self.request.path != '/logout'):
            # Admins/devs are sometimes logged in through google, but not our
            # site, if they visit /admin pages. This is because app.yaml
            # requires admin login, and directs them to google sign in without
            # talking to our normal /login process. We can clean up this
            # situation by logging them in here.
            user = self.authenticate('google')
        else:
            user = self.get_current_user()

        # Give every request handler an api in the context of the current user.
        # Don't do this when a user isn't present.
        logging.info("BaseHandler:Dispatch with user: {}".format(user))
        self.api = Api(user)

        try:
            # Call the overridden dispatch(), which has the effect of running
            # the get() or post() etc. of the inheriting class.
            webapp2.RequestHandler.dispatch(self)

        finally:
            # ** Code to run after all handlers goes here. ** #

            # Save all sessions.
            self.session_store.save_sessions(self.response)

    def clean_up_users(self, session_key):
        """Brings the three representations of users into alignment: the entity
        in the datastore, the id in the session, and the cached object saved as
        a property of the request handler."""
        id = self.session.get(session_key)
        attr = '_' + session_key
        cached_user = getattr(self, attr, None)
        if not id:
            # clear the cached user b/c the session is empty
            setattr(self, attr, None)
        elif not cached_user or id != cached_user.uid:
            # the cached user is invalid, try to restore from the session...
            datastore_user = User.get_by_id(id)
            if datastore_user:
                # found the user defined by the session; cache them
                setattr(self, attr, datastore_user)
            else:
                # could NOT find the user; clear everything
                del self.session[session_key]
                setattr(self, attr, None)
        # Make sure the session keys always exist, even if they are empty.
        if session_key not in self.session:
            self.session[session_key] = None
        logging.info("BaseHandler.clean_up_users")
        logging.info("session.{}: {}".format(
            session_key, self.session.get(session_key)))
        logging.info("{}: {}".format(
            session_key, getattr(self, attr)))

    def get_current_user(self, method=None):
        """Get the logged in user, preferring the impersonated user.

        The method argument can override this behavior. If overriding and the
        requested type of user is not present, will return None.
        """

        # Check that the session matches the cached user entites.
        self.clean_up_users('user')
        self.clean_up_users('impersonated_user')

        if method == 'normal':
            return self._user or None
        elif method == 'impersonated':
            return self._impersonated_user or None
        else:
            return self._impersonated_user or self._user or None

    def impersonate(self, target):
        """Use the website as if you were someone else.

        Raises: PermissionDenied
        """
        normal_user = self.get_current_user(method='normal')
        if normal_user.is_admin:
            # set the impersonated user
            self.session['impersonated_user'] = target.uid
            self._impersonated_user = target.key.get()
        else:
            raise PermissionDenied("Only admins may impersonate.")

    def stop_impersonating(self):
        self.session['impersonated_user'] = None

    def get_third_party_auth(self, auth_type, facebook_access_token=None):
        """Wrangle and return authentication data from third parties.

        Args:
            auth_type: str, either 'google', or 'facebook'
            facebook_access_token: str, returned by the facebook javasript sdk
                when user logs in.
        Returns tuple of:
            dictionary of user information, which will always contain
                the key 'auth_id', or None if no third-party info is found.
            error as a string
        """
        if auth_type == 'google':
            gae_user = app_engine_users.get_current_user()
            if not gae_user:
                logging.error("No google login found.")
                return (None, 'credentials_missing')
            # Get user first and last names from nickname
            first_name = None
            last_name = None
            if gae_user.nickname():
                nickname = gae_user.nickname()
                if ' ' in nickname:
                    first_name = nickname.split(' ')[0]
                    last_name = nickname.split(' ')[1]
                else:
                    if '@' in nickname:
                        first_name = nickname.split('@')[0]
                    else:
                        first_name = nickname
            # Combine fields in user keyword arguments
            user_kwargs = {
                'auth_id': User.get_auth_id(auth_type, gae_user.user_id()),
                'email': gae_user.email(),
                'google_id': gae_user.user_id(),
                'first_name': first_name,
                'last_name': last_name,
            }
        elif auth_type == 'facebook':
            fb_api = Facebook(config.facebook_app_id)
            fb_api.set_access_token(facebook_access_token)
            me = fb_api.get_myself()

            if me:
                if not hasattr(me, 'email'):
                    # Facebook users might not have an email address, or they
                    # might refuse to share it with us. We can't move forward
                    # without a way to contact them, so treat it as if their
                    # credentials were missing.
                    logging.warning("Found fb user, but they had no email.")
                    return (None, 'email_not_found')

                user_kwargs = {
                    'auth_id': User.get_auth_id(auth_type, me.id),
                    'email': me.email,
                    'facebook_id': me.id,
                    'first_name': me.first_name,
                    'last_name': me.last_name,
                }
            else:
                # The connection between PERTS and facebook is expired or has
                # been used with the GraphAPI already.
                logging.error("Facebook connection expired.")
                return (None, 'credentials_missing')

        return (user_kwargs, None)

    def authenticate(self, auth_type, email=None, password=None,
                     facebook_access_token=None):
        """Takes various kinds of credentials (email/password, google
        account) and logs you in.

        Returns:
          User entity             the user has been successfully authenticated
          'credentials_invalid'   either because a password is wrong or no
                                  account exists for those credentials
          'credentials_missing'   looked for credentials but didn't find any of
                                  the appropriate kind.
          'email_not_found'       the user authenticated through a third party,
                                  but they didn't have an email address.
          'email_exists:[auth_type]'  the supplied credentials are invalid AND
                                      a user with the same email exists with
                                      another auth type.
        """
        # fetch matching users
        if auth_type == 'own':
            if email is None or password is None:
                return 'credentials_missing'
            auth_id = User.get_auth_id(auth_type, email.lower())

        elif auth_type in ['google', 'facebook']:
            user_kwargs, error = self.get_third_party_auth(
                auth_type, facebook_access_token)
            if error:
                return error
            elif not user_kwargs:
                return 'credentials_missing'
            auth_id = user_kwargs['auth_id']

        # Fetch 2 b/c that's sufficient to detect multiple matching users.
        user_results = (
            User.query(User.deleted == False, User.auth_id == auth_id)
                .order(User.created)
                .fetch(2))

        # interpret the results of the query
        num_matches = len(user_results)
        if num_matches is 0:
            # Make it easy for devs to become admins.
            if (auth_type == 'google' and
                    app_engine_users.is_current_user_admin()):
                return self.register('google')
            # If a user with this email already exists, advise the client.
            # This step isn't necessary with google or facebook auth_types, b/c
            # we always try to register right after if logging in fails, and
            # register takes care of this part.
            if auth_type == 'own':
                matching_user = User.query(User.deleted == False,
                                           User.email == email).get()
                if matching_user:
                    return 'email_exists:' + matching_user.auth_type
            # no users with that auth_id, invalid log in
            return 'credentials_invalid'
        elif num_matches > 1:
            logging.error(u"More than one user matches auth info: {}."
                          .format(user_kwargs))
            # We'll let the function pass on and take the first of multiple
            # duplicate users, which will be the earliest-created one.

        # else num_matches is 1, the default case, and we can assume there was
        # one matching user
        user = user_results[0]

        # For direct authentication, PERTS is in charge of checking their
        # credentials, so validate the password.
        if auth_type == 'own':
            # A user-specific salt AND how many "log rounds" (go read about key
            # stretching) should be used is stored IN the user's hashed
            # password; that's why it's an argument here.
            # http://pythonhosted.org/passlib/
            if not User.verify_password(password, user.hashed_password):
                # invalid password for this email
                return 'credentials_invalid'

        # If we got this far, all's well, log them in and return the matching
        # user
        self.log_in(user)
        return user

    def register(self, auth_type, first_name=None, last_name=None, email=None,
                 password=None, facebook_access_token=None, should_subscribe=True):
        """Logs in users and registers them if they're new.

        Returns:
          User entity                 registration successful
          'credentials_missing'       looked for credentials but didn't find
                                      any of the appropriate kind.
          'email_exists:[auth_type]'  a user with that email already exists,
                                      with the specified auth type. In rare
                                      cases, we may know the email exists
                                      already, but not be able to query
                                      for it (gotta love eventual consistency),
                                      in which case the auth type will be
                                      'unknown'.
        """
        if auth_type not in config.auth_types:
            raise Exception("Bad auth_type: {}.".format(auth_type))
        if auth_type == 'own':
            if None in [email, password]:
                return 'credentials_missing'
            creation_kwargs = {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'auth_id': User.get_auth_id(auth_type, email),
                'hashed_password': User.hash_password(password),
            }

        # These are the third party identity providers we currently know
        # how to handle. See util_handlers.BaseHandler.get_third_party_auth().
        elif auth_type in ['google', 'facebook']:
            creation_kwargs, error = self.get_third_party_auth(
                auth_type, facebook_access_token)
            if error:
                return error
            elif not creation_kwargs:
                return 'credentials_missing'

        # Make it easy for devs to become admins.
        if auth_type == 'google' and app_engine_users.is_current_user_admin():
            creation_kwargs['is_admin'] = True

        # Pass through subscription parameter
        # Currently defaults true (planning to change later)
        creation_kwargs['should_subscribe'] = should_subscribe

        email = creation_kwargs['email']

        # Try to register the user. If a user with the same email already
        # exists, we'll get a DuplicateUser exception.
        try:
            user = User.create(**creation_kwargs)
        except DuplicateUser:
            # Attempt to retrieve the user entity which already exists.
            user = User.query(User.email == email).get()
            logging.info('Exception case with UserRegister')
            return 'email_exists:' + (user.auth_type if user else 'unknown')

        logging.info("BaseHandler created user: {}".format(user))

        # Registration succeeded; set them up.
        user.put()

        self.log_in(user)

        short_name = user.first_name if user.first_name else ''
        if user.first_name and user.last_name:
            full_name = user.first_name + ' ' + user.last_name
        else:
            full_name = user.username

        # Send them an email to confirm that they have registered.
        mandrill.send(
            to_address=email,
            subject="Welcome to the BELE Library",
            template="signup_confirmation.html",
            template_data={
                'short_name': short_name,
                'full_name': full_name,
                'user': user,
                'domain': 'https://{}'.format(os.environ['HOSTING_DOMAIN']),
                'year': datetime.date.today().year,
            },
        )

        logging.info(u'BaseHandler.register()')
        logging.info(u"Sending an email to: {}.".format(email))

        return user

    def log_in(self, user):
        logging.info("Logging in user: {}".format(user))
        self.session['user'] = user.uid
        self.api = Api(user)
        # Updates last login!
        user.last_login = datetime.datetime.now()
        user.put()

    def log_out(self):
        redirect = self.request.get('redirect') or '/'

        self.response.delete_cookie('ACSID')
        self.response.delete_cookie('SACSID')

        # The name of the login cookie is defined in
        # url_handlers.BaseHandler.session()
        self.response.delete_cookie(config.session_cookie_name)

        # @todo: clear facebook logins also

        # This cookie is created when logging in with a google account with
        # the app engine sdk (on localhost).
        self.response.delete_cookie('dev_appserver_login')
        self._user = None
        self._impersonated_user = None

    @webapp2.cached_property
    def session(self):
        """Allows set/get of session data within handler methods.
        To set a value: self.session['foo'] = 'bar'
        To get a value: foo = self.session.get('foo')"""
        # Returns a session based on a cookie. Other options are 'datastore'
        # and 'memcache', which may be useful if we continue to have bugs
        # related to dropped sessions. Setting the name is critical, because it
        # allows use to delete the cookie during logout.
        # http://webapp-improved.appspot.com/api/webapp2_extras/sessions.html
        return self.session_store.get_session(name=config.session_cookie_name,
                                              backend='securecookie')
