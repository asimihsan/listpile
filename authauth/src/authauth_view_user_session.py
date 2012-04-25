import os
import sys

import tornado
from tornado.options import define, options
import redis
import logging

import user_session

# ----------------------------------------------------------------------------
#   Configuration constants. Note that the redis hostname and port are
#   already defined in the database file. There must be a better way
#   of doing this.
# ----------------------------------------------------------------------------
define("redis_database_id_for_user_sessions", default=None, type=int, help="Database ID for user sessions")
# ----------------------------------------------------------------------------

class UserSessionManager(object):
    def __init__(self):
        # Start a connection to the redis to the database ID that stores
        # the user session data.
        self.r = redis.StrictRedis(host=options.redis_hostname,
                                   port=options.redis_port,
                                   db=options.redis_database_id_for_user_sessions)
        #self.r.flushdb()            
        
    def is_user_authorized(self, user_id):
        """ Determine if a given user_id is authorized to be
        performing operations."""
        logger = logging.getLogger("UserSessionManager.is_user_authorized")
        logger.debug("Entry. user_id: %s" % (user_id, ))
        if self.r.exists(user_id):
            return_value = True
        else:
            return_value = False
        logger.debug("returning: %s" % (return_value, ))
        return return_value
        
    def deauthorize_user(self, user_id):
        """ Mark a given user ID as no longer authorized to
        perform operations. Could do this if they e.g. log out,
        are deleted, etc. """
        logger = logging.getLogger("UserSessionManager.deauthorize_user")
        logger.debug("Entry. user_id: %s" % (user_id, ))      
        assert(self.is_user_authorized(user_id))
        self.r.delete(user_id)
        
    def authorize_user(self, user_id, authentication_type):
        """ Mark a given user ID as permitted to perform operations
        on the server.
        
        As the only way to get here is via an authentication handler
        we know how this user got authenticated (i.e. Google,
        Facebook, Twitter, BrowserID, or API call). Let's store that
        as the hash's first key. authentication_type, hence, is a
        string from the following list:
        -   "facebook"
        -   "google"
        -   "twitter"
        -   "browserid"
        -   "api"
        
        Also, set the user to expire in an hour.
        """
        logger = logging.getLogger("UserSessionManager.authorize_user")
        logger.debug("Entry. user_id: %s, authentication_type: %s" % (user_id, authentication_type))        
        assert(not self.is_user_authorized(user_id))
        assert(authentication_type in ["facebook", "google", "twitter", "browserid", "api"])
        self.r.hset(user_id, "authentication_type", authentication_type)        
        self.set_user_expiry(user_id)
    
    def set_user_expiry(self, user_id, expiry_time = 60 * 60):
        """ Set the user to expire in an hour. """
        logger = logging.getLogger("UserSessionManager.set_user_expiry")
        logger.debug("Entry. user_id: %s, expiry_time: %s" % (user_id, expiry_time))
        self.r.expire(user_id, expiry_time)
    
    def get_all_user_session_data(self, user_id):
        """ Return the user session data as a dictionary. If the user
        is not authorized returns None."""
        logger = logging.getLogger("UserSessionManager.get_all_user_session_data")
        logger.debug("Entry. user_id: %s" % (user_id, ))        
        if not self.is_user_authorized(user_id):
            logger.debug("User is not authorized, so no data.")
            return None
        data = self.r.hgetall(user_id)
        logger.debug("Returning: %s" % (data, ))
        return data

    def get_user_session_datum(self, user_id, key):
        """ Get a particular key from the user session data. """
        logger = logging.getLogger("UserSessionManager.get_user_session_datum")
        logger.debug("Entry. user_id: %s" % (user_id, key))        
        if not self.is_user_authorized(user_id):
            logger.debug("User is not authorized, so no data.")
            return None
        data = self.r.hget(user_id, key)
        logger.debug("Returning: %s" % (data, ))
        return data
        
    def set_user_session_datum(self, user_id, key, value):
        """ Set a key/value pair on the user session data. """
        logger = logging.getLogger("UserSessionManager.set_user_session_datum")
        logger.debug("Entry. user_id: %s, key: %s, value: %s" % (user_id, key, value))        
        assert(self.is_user_authorized(user_id))
        self.r.hset(user_id, key, value)
        
    def delete_user_session_datum(self, user_id, key):
        """ Delete a key/value pair."""
        logger = logging.getLogger("UserSessionManager.delete_user_session_datum")
        logger.debug("Entry. user_id: %s, key: %s" % (user_id, key))        
        assert(self.is_user_authorized(user_id))
        self.r.hdel(user_id, key)
