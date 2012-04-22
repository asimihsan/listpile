#!/usr/bin/env python2.7

# ---------------------------------------------------------------------------
# Copyright (c) 2012 Asim Ihsan (asim dot ihsan at gmail dot com)
# Distributed under the MIT/X11 software license, see the accompanying
# file license.txt or http://www.opensource.org/licenses/mit-license.php.
# ---------------------------------------------------------------------------

import os
import sys
import argparse
import json
import traceback

import gevent
import gevent.monkey; gevent.monkey.patch_all()
from gevent_zeromq import zmq

# ----------------------------------------------------------------------
#   Logging.
# ----------------------------------------------------------------------
import logging
import logging.handlers

APP_NAME = 'authauth_model'
logger = logging.getLogger(APP_NAME)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)
logger = logging.getLogger(APP_NAME)
# ----------------------------------------------------------------------

import authauth_model_database

class InvalidMessageTypeException(Exception):
    def __init__(self, reason):
        self.reason = reason
    def __str__(self):
        return repr(self.reason)

class InvalidMessageFormatException(Exception):
    def __init__(self, reason):
        self.reason = reason
    def __str__(self):
        return repr(self.reason)

valid_message_types = set([ \
                            "ping",
                            "get_user",
                            "add_user",
                          ])
def validate_message(message):
    if "message_type" not in message:
        raise InvalidMessageFormatException("message_type field not present")
    message_type = message["message_type"]
    if message_type not in valid_message_types:
        raise InvalidMessageTypeException("message_type '%s' not recognised" % (message_type, ))
    if message_type == "get_user":
        if "user_type" not in message:
            raise InvalidMessageFormatException("'get_user' message missing 'user_type' field")
        user_type = message["user_type"]
        if user_type == "google":
            if "email" not in message:
                raise InvalidMessageFormatException("'get_user' for 'google' user type missing 'email' field")
    if message_type == "add_user":
        if "user_type" not in message:
            raise InvalidMessageFormatException("'get_user' message missing 'user_type' field")
        user_type = message["user_type"]
        if user_type == "google":
            if "email" not in message:
                raise InvalidMessageFormatException("'get_user' for 'google' user type missing 'email' field")

def handle_server_request(server, database):
    logger = logging.getLogger("%s.handle_server_request" % (APP_NAME, ))
    message_encoded = server.recv()
    try:
        message_decoded = json.loads(message_encoded)
    except:
        return None
    try:
        validate_message(message_decoded)
    except:
        logger.exception("unhandled exception")
        return None

    message_type = message_decoded["message_type"]
    if message_type == "ping":
        handle_ping(server)
    elif message_type == "get_user":
        handle_get_user(server, message_decoded, database)
    elif message_type == "add_user":
        handle_add_user(server, message_decoded, database)

def handle_ping(server):
    message_type = "pong"
    message_args = {"status": "ok"}
    return send_message(server, message_type, message_args)

def handle_get_user(server, message_decoded, database):
    # ------------------------------------------------------------------------
    #   Validate assumptions.
    # ------------------------------------------------------------------------
    assert("user_type" in message_decoded)
    # ------------------------------------------------------------------------

    message_type = "get_user_response"
    user_type = message_decoded["user_type"]
    if user_type == "google":
        assert("email" in message_decoded)
        email = message_decoded["email"]
        google_user = database.get_google_user(email)
        if google_user is None:
            message_args = {"status": "ok",
                            "user_id": None}
        else:
            user_id = google_user.user_id
            message_args = {"status": "ok",
                            "user_id": user_id}
        return send_message(server, message_type, message_args)

def handle_add_user(server, message_decoded, database):
    # ------------------------------------------------------------------------
    #   Validate assumptions.
    # ------------------------------------------------------------------------
    assert("user_type" in message_decoded)
    # ------------------------------------------------------------------------

    message_type = "add_user_response"
    user_type = message_decoded["user_type"]
    if user_type == "google":
        assert("email" in message_decoded)
        email = message_decoded["email"]
        google_user = database.add_google_user(email)
        user_id = google_user.user_id
        message_args = {"status": "ok",
                        "user_id": user_id}
        return send_message(server, message_type, message_args)

def get_base_message():
    rv = {"version": "1.0"}
    return rv

def send_message(socket, message_type, message_args = None):
    if not message_args:
        message_args = {}

    message = get_base_message()
    message["message_type"] = message_type
    for (key, value) in message_args.iteritems():
        message[key] = value
    socket.send(json.dumps(message))

def get_args():
    parser = argparse.ArgumentParser("Authenticate and authorise users.")
    parser.add_argument("--zeromq_binding",
                        dest="zeromq_binding",
                        metavar="ZEROMQ_BINDING",
                        required=True,
                        help="ZeroMQ binding we REP on for clients.")
    parser.add_argument("--database_filepath",
                        dest="database_filepath",
                        metavar="FILEPATH",
                        required=True,
                        help="Full path to the database filepath to use.")
    parser.add_argument("--verbose",
                        dest="verbose",
                        action='store_true',
                        default=False,
                        help="Enable verbose debug mode.")
    parser.add_argument("--empty_database",
                        dest="empty_database",
                        action='store_true',
                        default=False,
                        help="Empty the persistent store on startup.")
    args = parser.parse_args()
    return args

def main():
    args = get_args()
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        ch.setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled")

    database = authauth_model_database.Database(args.database_filepath,
                                                empty_database = args.empty_database)

    # ------------------------------------------------------------------------
    #   Bind to the ZeroMQ REP binding for client requests.
    # ------------------------------------------------------------------------
    context = zmq.Context(1)
    server = context.socket(zmq.REP)
    server.bind(args.zeromq_binding)
    # ------------------------------------------------------------------------

    # ------------------------------------------------------------------------
    #   Set up a ZeroMQ poller.
    # ------------------------------------------------------------------------
    poller = zmq.Poller()
    poller.register(server, zmq.POLLIN)
    POLL_INTERVAL = 1000
    # ------------------------------------------------------------------------

    # ------------------------------------------------------------------------
    #   Poll for events.
    # ------------------------------------------------------------------------
    while True:
        socks = dict(poller.poll(POLL_INTERVAL))
        if socks.get(server, None) == zmq.POLLIN:
            handle_server_request(server, database)
    # ------------------------------------------------------------------------

if __name__ == "__main__":
    main()
