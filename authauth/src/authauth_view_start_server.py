#!/usr/bin/env python2.7

import tornado
import tornado.ioloop
import tornado.web
import tornado.auth
import tornado.escape
import tornado.httpserver

import tornado.options
from tornado.options import define, options

import os
import sys
import json
import base64
import uuid
import pprint

from authauth_view_base_request_handlers import BasePageHandler

from authauth_view_auth_request_handlers import LoginGoogleHandler
from authauth_view_auth_request_handlers import LoginFacebookHandler
from authauth_view_auth_request_handlers import LoginTwitterHandler
from authauth_view_auth_request_handlers import LoginBrowserIDHandler
from authauth_view_auth_request_handlers import LoginApiHandler
from authauth_view_auth_request_handlers import LogoutHandler

# ----------------------------------------------------------------------
#   Constants.
# ----------------------------------------------------------------------
APP_NAME = 'authauth_view_start_server'
LOG_PATH = os.path.join(__file__, os.pardir)
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
#   Configuration variables that we require.
# ----------------------------------------------------------------------
define("http_listen_ip_address", default=None, help="HTTP listen IP address")
define("http_listen_port", default=None, type=int, help="HTTP listen port")
define("number_of_processes", default=None, type=int, help="Number of processes")
define("debug_mode", default=None, help="Tornado debug mode enabled or not")

# If you want to use the old-style OAuth1 Facebook authentication API then
# uncomment these lines, as Tornado requires forward-declaration of
# configuration variables, and you need to pass in these guys into the
# Application constructor.
#define("facebook_app_id", default=None, help="Facebook app ID")
#define("facebook_app_secret", default=None, help="Facebook app secret")

define("twitter_consumer_key", default=None, help="Twitter app consumer key")
define("twitter_consumer_secret", default=None, help="Twitter app consumer secret")

define("test", default=None, help="Set if you're doing UT/FV")
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
#   Logging.
# ----------------------------------------------------------------------
import logging
import logging.handlers
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

if not os.path.isdir(LOG_PATH):
    os.makedirs(LOG_PATH)
log_filename = os.path.join(LOG_PATH, "%s.log" % (APP_NAME, ))
ch2 = logging.handlers.RotatingFileHandler(log_filename,
                                           maxBytes=10*1024*1024,
                                           backupCount=5)
ch2.setFormatter(formatter)
logger.addHandler(ch2)

logger = logging.getLogger(APP_NAME)
# ----------------------------------------------------------------------

class MainHandler(BasePageHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        logger = logging.getLogger("MainHandler.get")
        logger.debug("entry.")
        if self.current_user:
            logger.debug("Current user is authorized as: %s" % (self.current_user, ))
            new_url = self.reverse_url("ListsHandler")
            logger.debug("Redirecting to: %s" % (new_url, ))
            self.redirect(new_url)
            return
        data = {}
        data['user'] = None
        lists = []
        data['lists'] = lists
        data['title'] = "Help Me Shop"
        self.render("index.html", **data)

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),

            (r"/login/api", LoginApiHandler),
            (r"/login/api/", LoginApiHandler),
            (r"/login/google", LoginGoogleHandler),
            (r"/login/google/", LoginGoogleHandler),
            (r"/login/facebook", LoginFacebookHandler),
            (r"/login/facebook/", LoginFacebookHandler),
            (r"/login/twitter", LoginTwitterHandler),
            (r"/login/twitter/", LoginTwitterHandler),
            (r"/login/browserid", LoginBrowserIDHandler),
            (r"/login/browserid/", LoginBrowserIDHandler),
            (r"/logout", LogoutHandler),
            (r"/logout/", LogoutHandler),

        ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), 'templates'),
            static_path=os.path.join(os.path.dirname(__file__), 'static'),
            xsrf_cookies=True,
            gzip=True,

            # If you generate the cookie from scratch then server restarts will
            # render old cookies invalid. This affects fault-tolerance!
            cookie_secret='ANrq+RCiRu2VQQIdXOw2rQVT/BvavUI2nEA9TrfjesQ=',
            #cookie_secret=base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes),

            # These two lines are required for the old-style OAuth1 Facebook
            # authentication API. So just leave them here, might come in handy
            # one day. If you uncomment these then you'll need to 'define' these
            # configuration variables at the top as well.
            #facebook_api_key=options.facebook_app_id,
            #facebook_secret=options.facebook_app_secret,

            twitter_consumer_key=options.twitter_consumer_key,
            twitter_consumer_secret=options.twitter_consumer_secret,
        )
        if options.debug_mode:
            settings['debug'] = True
        tornado.web.Application.__init__(self, handlers, **settings)

if __name__ == "__main__":
    logger.info("starting")

    # ------------------------------------------------------------------------
    #   Import settings.
    #
    #   -   Always load the config file in the same directory as this file
    #       first.
    #   -   If it exists load a file with the same filename in the test
    #       directory, to allow us a special case of listening on localhost.
    # ------------------------------------------------------------------------
    command_line_args = tornado.options.parse_command_line()

    this_directory = os.path.dirname(__file__)
    config_paths = [os.path.join(this_directory, "authauth_view_server.conf")]

    if options.test:
        test_config_path = os.path.abspath(os.path.join(this_directory, os.pardir, "test", "authauth_view_server.conf"))
        logger.debug("test_config_path: %s" % (test_config_path, ))
        if os.path.isfile(test_config_path):
            config_paths.append(test_config_path)
    logger.info("config files to use, in order: %s" % (pprint.pformat(config_paths), ))
    for filepath in config_paths:
        assert(os.path.isfile(filepath))
        tornado.options.parse_config_file(filepath)
    # ------------------------------------------------------------------------

    logger.debug("start listening on %s:%s" % (options.http_listen_ip_address, options.http_listen_port))
    http_server = tornado.httpserver.HTTPServer(Application(),
                                                xheaders=True)
    http_server.bind(port = options.http_listen_port,
                     address = options.http_listen_ip_address)

    # Debug mode only supports one process in multi-processing mode.
    if options.debug_mode:
        number_of_processes = 1
    else:
        number_of_processes = options.number_of_processes

    http_server.start(number_of_processes)
    tornado.ioloop.IOLoop.instance().start()

