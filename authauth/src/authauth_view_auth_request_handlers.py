# ----------------------------------------------------------------------------
#   TODO
#
# ----------------------------------------------------------------------------

import tornado
import tornado.gen
import tornado.web
import tornado.auth
import tornado.httpclient
import urllib
from tornado.options import define, options

import os
import sys
import logging
import pprint
import urlparse

from authauth_view_base_request_handlers import BasePageHandler
from authauth_view_base_request_handlers import BaseLoginHandler

from authauth_view_utilities import normalize_uuid_string

# --------------------------------------------------------------------
# NOTES
#
# We use a secure cookie to prove the user has authenticated with
# our server, and user session data to prove the user should
# still be logged in and what session data they need.
#
# The secure cookie is an HMAC composed of the user_id, a timestamp,
# and a secret that only the server knows. Hence it is unforgeable
# and must have come from us.
# --------------------------------------------------------------------

# ----------------------------------------------------------------------------
#   Configuration constants.
# ----------------------------------------------------------------------------
define("base_uri", default=None, help="Base URI where the site is hosted.")
define("facebook_app_id", default=None, help="Facebook app ID")
define("facebook_app_secret", default=None, help="Facebook app secret")
# ----------------------------------------------------------------------------

class LogoutHandler(BasePageHandler):
    """ Just delete the user session data for the current user, this will
    log them out. If noone is logged in then ignore.

    Let's do ourselves a favour and delete all database cache elements to
    do with the user as well. The user implicitly expects the logout to
    result in a clean slate, so let's give it to them.
    """
    def get(self):
        logger = logging.getLogger("LogoutHandler.get")
        logger.debug("entry.")
        if self.current_user:
            logger.debug("User currently logged in: %s" % (self.current_user, ))
            self.user_session.deauthorize_user(self.current_user)
            normalized_user_id = normalize_uuid_string(self.current_user)
            self.db.expire_cache(normalized_user_id)
        self.redirect("/")

# ----------------------------------------------------------------------------
#   RequestHandler that deals with API key authentication.
#
#   Note that this isn't a way of adding a new user. You must have already
#   authorized using another authorization method, which gives you an
#   API key, in order to log in.
# ----------------------------------------------------------------------------
class LoginApiHandler(BaseLoginHandler):
    @tornado.web.asynchronous
    def get(self):
        logger = logging.getLogger("LoginApiHandler.get")
        logger.debug("entry")
        data = {}
        if self.current_user:
            logging.debug("User is already authorized as user: %s." % (self.current_user, ))
            self.redirect("/")
        else:
            data['user'] = None
            data['title'] = "API key login (Help Me Shop)"
            self.render("login_api.html", **data)

    @tornado.web.asynchronous
    @tornado.gen.engine
    def post(self):
        logger = logging.getLogger("LoginApiHandler.post")
        logger.debug("entry.")
        api_secret_key = self.get_argument("api_secret_key")
        logger.debug("api_secret_key: %s" % (api_secret_key, ))
        user_id = yield tornado.gen.Task(self.db.get_user_id_from_api_secret_key,
                                         api_secret_key)
        logger.debug("user_id: %s" % (user_id, ))
        if not user_id:
            # User does not exist.
            raise tornado.web.HTTPError(403, "API key not authorized.")
        self.set_secure_cookie_and_authorization(user_id, "api")
        self.redirect("/")
        self.finish()

# ----------------------------------------------------------------------------
#   RequestHandler that deals with Mozilla BrowserID authentication.
# ----------------------------------------------------------------------------
class LoginBrowserIDHandler(BaseLoginHandler):
    @tornado.web.asynchronous
    def post(self):
        logger = logging.getLogger("LoginBrowserIDHandler.get")
        logger.debug("entry")
        logger.debug("request: \n%s" % (pprint.pformat(self.request), ))

        adjust_request_host_to_referer(self.request)

        assertion = self.get_argument('assertion')
        domain = self.request.host
        data = {'assertion': assertion,
                'audience': domain}
        logger.debug('data: %s' % (data, ))

        http_client = tornado.httpclient.AsyncHTTPClient()
        url = 'https://browserid.org/verify'

        response = http_client.fetch(url,
                                     method='POST',
                                     body=urllib.urlencode(data),
                                     callback=self.async_callback(self._on_response))

    @tornado.gen.engine
    def _on_response(self, response):
        logger = logging.getLogger("LoginBrowserIDHandler._on_response")
        logger.debug("entry. response: %s" % (response, ))
        struct = tornado.escape.json_decode(response.body)
        logger.debug("response struct: %s" % (struct, ))
        if struct['status'] != 'okay':
            raise tornado.web.HTTPError(400, "BrowserID status not okay")

        # Does a user already exist for these BrowserID credentials?
        # BrowserID credentials are uniquely identified by the email
        # address.
        email = struct['email']
        user_id = yield tornado.gen.Task(self.db.get_user_id_from_browserid_email,
                                 email)
        logger.debug("user_id: %s" % (user_id, ))
        if not user_id:
            # User does not exist.
            logger.debug("User does not exist.")
            user_id = yield tornado.gen.Task(self.db.create_user, "regular")
            logger.debug("user_id: %s" % (user_id, ))
            rc = yield tornado.gen.Task(self.db.create_auth_browserid,
                                        email,
                                        user_id)
            logger.debug("create_auth_browserid rc: %s" % (rc, ))
            assert(rc == True)

        self.set_secure_cookie_and_authorization(user_id, "browserid")

        self.set_header("Content-Type", "application/json; charset=UTF-8")
        response = {'next_url': '/'}
        self.write(tornado.escape.json_encode(response))
        self.finish()

# ----------------------------------------------------------------------------
#   RequestHandler that deals with Twitter authentication.
# ----------------------------------------------------------------------------
class LoginTwitterHandler(BaseLoginHandler, tornado.auth.TwitterMixin):
    @tornado.web.asynchronous
    def get(self):
        logger = logging.getLogger("LoginTwitterHandler.get")
        logger.debug("entry")

        # We'll get a "denied" GET paramater back if the user has refused
        # to authorise us.
        denied = self.get_argument("denied", None)
        logger.debug("denied: %s" % (denied, ))
        if denied:
            raise tornado.web.HTTPError(500, "Twitter authentication failed. User refused to authorize.")

        oauth_token = self.get_argument("oauth_token", None)
        logger.debug("oauth_token: %s" % (oauth_token, ))
        if oauth_token:
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        adjust_request_host_to_referer(self.request)
        self.authorize_redirect()

    @tornado.gen.engine
    def _on_auth(self, user):
        logger = logging.getLogger("LoginTwitterHandler._on_auth")
        logger.debug("entry. user:\n%s" % (pprint.pformat(user), ))
        if not user:
            raise tornado.web.HTTPError(500, "Twitter authentication failed")
        assert("username" in user)

        # Does a user already exist for these Twitter credentials?
        # Twitter credentials are uniquely identified by the username
        user_id = yield tornado.gen.Task(self.db.get_user_id_from_twitter_username,
                                         user["username"])
        logger.debug("user_id: %s" % (user_id, ))
        if not user_id:
            # User does not exist.
            logger.debug("User does not exist.")
            assert("profile_image_url" in user)

            user_id = yield tornado.gen.Task(self.db.create_user, "regular")
            logger.debug("user_id: %s" % (user_id, ))
            rc = yield tornado.gen.Task(self.db.create_auth_twitter,
                                        user["username"],
                                        user_id,
                                        user["profile_image_url"])
            logger.debug("create_auth_twitter rc: %s" % (rc, ))
            assert(rc == True)

        self.set_secure_cookie_and_authorization(user_id, "twitter")
        self.redirect("/")
# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
#   RequestHandler that deals with Facebook authentication.
#
#   redirect_uri must be an absolute path, or else the Facebook authentication
#   API throws an error and references the OAuth RFC. Hence you must know
#   the full URI of where you want Facebook to return your user.
#
#   For more elaboration on the available "scope" parameters see:
#   https://developers.facebook.com/docs/reference/api/permissions/
#
#   Note that, unlike Twitter or Google, Facebook does not have an explicit
#   "do not accept" choice for the user.
# ----------------------------------------------------------------------------
class LoginFacebookHandler(BaseLoginHandler, tornado.auth.FacebookGraphMixin):
    @tornado.web.asynchronous
    def get(self):
        logger = logging.getLogger("LoginFacebookHandler.get")
        logger.debug("entry")

        redirect_uri = '%s/login/facebook/' % (options.base_uri, )

        code = self.get_argument("code", False)
        logger.debug("code: %s" % (code, ))
        if code:
            self.get_authenticated_user(
                redirect_uri=redirect_uri,
                client_id=options.facebook_app_id,
                client_secret=options.facebook_app_secret,
                code=code,
                callback=self.async_callback(self._on_login))
            return
        adjust_request_host_to_referer(self.request)
        self.authorize_redirect(redirect_uri=redirect_uri,
                                client_id=options.facebook_app_id,
                                extra_params={"scope": "read_stream,offline_access"})

    @tornado.gen.engine
    def _on_login(self, user):
        logger = logging.getLogger("LoginFacebookHandler._on_login")
        logger.debug("entry. user: %s" % (user, ))
        if not user:
            raise tornado.web.HTTPError(500, "Facebook authentication failed")
        assert("id" in user)

        # Does a user already exist for these Facebook credentials?
        # Facebook credentials are uniquely identified by the id
        user_id = yield tornado.gen.Task(self.db.get_user_id_from_facebook_id,
                                         user["id"])
        logger.debug("user_id: %s" % (user_id, ))
        if not user_id:
            # User does not exist.
            logger.debug("User does not exist.")
            assert("link" in user)
            assert("access_token" in user)
            assert("locale" in user)
            assert("first_name" in user)
            assert("last_name" in user)
            assert("name" in user)
            assert("picture" in user)

            user_id = yield tornado.gen.Task(self.db.create_user, "regular")
            logger.debug("user_id: %s" % (user_id, ))
            rc = yield tornado.gen.Task(self.db.create_auth_facebook,
                                        user["id"],
                                        user_id,
                                        user["link"],
                                        user["access_token"],
                                        user["locale"],
                                        user["first_name"],
                                        user["last_name"],
                                        user["name"],
                                        user["picture"])
            logger.debug("create_auth_facebook rc: %s" % (rc, ))
            assert(rc == True)

        self.set_secure_cookie_and_authorization(user_id, "facebook")
        self.redirect("/")

# ----------------------------------------------------------------------------
#   RequestHandler that deals with Facebook authentication. This is the
#   old-style OAuth1 that works but is depreciated in favour of the graph
#   mixin.
# ----------------------------------------------------------------------------
#class LoginFacebookHandler(BaseLoginHandler, tornado.auth.FacebookMixin):
#    @tornado.web.asynchronous
#    def get(self):
#        logger = logging.getLogger("LoginFacebookHandler.get")
#        logger.debug("entry")
#
#        session = self.get_argument("session", None)
#        logger.debug("session: %s" % (session, ))
#        if session:
#            self.get_authenticated_user(self.async_callback(self._on_auth))
#            return
#        self.authenticate_redirect()
#
#    def _on_auth(self, user):
#        logger = logging.getLogger("LoginFacebookHandler._on_auth")
#        logger.debug("entry. user: %s" % (user, ))
#        if not user:
#            raise tornado.web.HTTPError(500, "Facebook authentication failed")
#        assert("uid" in user)
#        self.set_secure_cookie("user", str(user["uid"]))
#        self.redirect("/")
# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
#   RequestHandler that deals with Google authentication.
# ----------------------------------------------------------------------------
class LoginGoogleHandler(BaseLoginHandler, tornado.auth.GoogleMixin):
    @tornado.web.asynchronous
    def get(self):
        logger = logging.getLogger("LoginGoogleHandler.get")
        logger.debug("entry. request: \n%s" % (pprint.pformat(self.request), ))

        # If openid_mode is None we have not authenticated yet.
        # If openid_mode is cancel the user has refused to
        # authorise us.
        # If openid_mode is id_res the user has authorised us.
        openid_mode = self.get_argument("openid.mode", None)
        logger.debug("openid_mode: %s" % (openid_mode, ))
        if openid_mode == "cancel":
            raise tornado.web.HTTPError(500, "Google authentication failed. User refused to authorize.")

        if openid_mode:
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return

        adjust_request_host_to_referer(self.request)
        self.authenticate_redirect()

    @tornado.gen.engine
    def _on_auth(self, user):
        print "Google _on_auth called"
        logger = logging.getLogger("LoginGoogleHandler._on_auth")
        logger.debug("entry. user: %s" % (user, ))
        if not user:
            raise tornado.web.HTTPError(500, "Google authentication failed")
        assert("email" in user)

        # Does a user already exist for these Google credentials?
        # Google credentials are uniquely identified by the email address.
        # !!AI TODO
        #user_id = yield tornado.gen.Task(self.db.get_user_id_from_google_email,
        #                                 user["email"])
        user_id = "userid"
        logger.debug("user_id: %s" % (user_id, ))
        if not user_id:
            # User does not exist.
            logger.debug("User does not exist.")
            assert("first_name" in user)
            assert("last_name" in user)
            assert("name" in user)
            assert("locale" in user)

            user_id = yield tornado.gen.Task(self.db.create_user, "regular")
            logger.debug("user_id: %s" % (user_id, ))
            rc = yield tornado.gen.Task(self.db.create_auth_google,
                                        user["email"],
                                        user_id,
                                        user["first_name"],
                                        user["last_name"],
                                        user["name"],
                                        user["locale"])
            logger.debug("create_auth_twitter rc: %s" % (rc, ))
            assert(rc == True)

        self.set_secure_cookie_and_authorization(user_id, "google")

        #!!AI TODO. We redirect to an entirely different IP:port, should
        # be configurable. In order to UT this we have another
        # simple server listening here.
        self.redirect("http://10.227.33.1:8001/login/google/successful/")
# ----------------------------------------------------------------------------

def adjust_request_host_to_referer(request):
    # --------------------------------------------------------------------
    #   We need to adjust the request's host field. This is because
    #   the architecture is:
    #       web client -> nginx -> haproxy -> tornado -> auth. server
    #   tornado thinks the request came from haproxy, which is
    #   on 127.0.0.1. We need to adjust the request to make it come from
    #   the public IP of the server, which nginx has passed on in the
    #   referer field.
    # --------------------------------------------------------------------
    logger = logging.getLogger("adjust_request_host_to_referer")
    logger.debug("entry.")
    referer = request.headers.get("Referer", None)
    if referer:
        scheme = request.headers.get("X-Scheme", "http")
        assert(scheme in ["http", "https"])
        if scheme == "http":
            port = 80
        else:
            port = 443
        new_host = "%s:%s" % (urlparse.urlparse(referer).netloc, port)
        logger.debug("Changed request host from %s to %s" % (request.host, new_host))
        request.host = new_host
    # --------------------------------------------------------------------
