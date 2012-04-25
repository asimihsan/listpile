
import logging
import tornado
from tornado.options import define, options
import re

# ----------------------------------------------------------------------------
#   Base request handler.
# ----------------------------------------------------------------------------
class BaseHandler(tornado.web.RequestHandler):
    REGEXP_BASE64 = re.compile("^[A-Za-z0-9-_=]+$")

    @property
    def db(self):
        """ Create a database connection when a request handler is called
        and store the connection in the application object.
        """
        if not hasattr(self.application, 'db'):
            self.application.db = None
            #self.application.db = database.DatabaseManager()
        return self.application.db

    @property
    def user_session(self):
        """ Create a redis connection to CRUD the current user's session
        data.
        """
        if not hasattr(self.application, 'user_session'):
            self.application.user_session = None
            #self.application.user_session = user_session.UserSessionManager()
        return self.application.user_session

    @staticmethod
    def validate_base64_parameter(parameter):
        """ Given a string in variable 'parameter' confirm that it is a
        URL safe base64 encoded string. """
        return BaseHandler.REGEXP_BASE64.search(parameter)
# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
#   Base page handler.
# ----------------------------------------------------------------------------
class BasePageHandler(BaseHandler):
    def get_current_user(self):
        """ Determine what the current user is. Return None if there is
        currently no authorized user. We do this in two cases,
        1) A user never logged in before.
        2) A user was logged in but their session expired.
        """
        user_id = self.get_secure_cookie("user")
        if not user_id:
            return None
        if not self.user_session.is_user_authorized(user_id):
            return None
        return user_id
# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
#   Base login handler.
# ----------------------------------------------------------------------------
class BaseLoginHandler(BasePageHandler):
    def set_secure_cookie_and_authorization(self, user_id, authorization_type):
        logger = logging.getLogger("BaseLoginHandler.set_secure_cookie_and_authorization")
        logger.debug("entry. user_id: %s, authorization_type: %s" % (user_id, authorization_type))
        self.set_secure_cookie('user', user_id)
        return
        # !!AI TODO
        if not self.user_session.is_user_authorized(user_id):
            logger.debug("User is not currently authorized.")
            self.user_session.authorize_user(user_id, authorization_type)
        else:
            # If the user is already authorized then just re-set their
            # authorization expiry time.
            logger.debug("User is already authorized.")
            self.user_session.set_user_expiry(user_id)
# ----------------------------------------------------------------------------



