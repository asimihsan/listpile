#!/usr/bin/env python2.7

# ---------------------------------------------------------------------------
# Copyright (c) 2012 Asim Ihsan (asim dot ihsan at gmail dot com)
# Distributed under the MIT/X11 software license, see the accompanying
# file license.txt or http://www.opensource.org/licenses/mit-license.php.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
#   test_model_basic.py: a set of basic tests that confirm that the authauth
#   server code exists at all. No functional or non-functional requirements
#   get tested. If tests fail here you're usually looking at missing modules,
#   a bad environment, etc.
# ---------------------------------------------------------------------------

import os
import sys
import zmq
import subprocess
from string import Template
import time
import json
import uuid

from nose.tools import raises, assert_false, assert_true, assert_not_equal, assert_equal, assert_less
from nose.plugins.skip import SkipTest, Skip
import unittest

# ---------------------------------------------------------------------------
#   Constants.
# ---------------------------------------------------------------------------
code_filepath = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, "src"))
assert(os.path.isdir(code_filepath))
script_under_test = os.path.join(code_filepath, "authauth_model.py")
assert(os.path.isfile(script_under_test))

CMD_TEMPLATE = Template(""" ${executable} --zeromq_binding ${zeromq_binding} --empty_database --database_filepath ${database_filepath} --verbose """)
SERVER_ZEROMQ_BINDING = "tcp://*:5556"
CLIENT_ZEROMQ_BINDING = "tcp://localhost:5556"
DATABASE_FILEPATH = "authauth.db"
# ---------------------------------------------------------------------------

class TimeoutException(Exception):
    pass

class TestBasic(unittest.TestCase):
    def _execute_command(self, command, capture_output = False):
        devnull = open(os.devnull, "rb+")
        if capture_output:
            process = subprocess.Popen(command,
                                       shell = True,
                                       stdin = devnull,
                                       stdout = subprocess.PIPE)
        else:
            process = subprocess.Popen(command,
                                       shell = True,
                                       stdin = devnull,
                                       stdout = devnull)
        return process

    def setUp(self):
        # --------------------------------------------------------------------
        #   Launch the authauth process.
        # --------------------------------------------------------------------
        self.process_cmd = CMD_TEMPLATE.substitute(executable = script_under_test,
                                                   zeromq_binding = SERVER_ZEROMQ_BINDING,
                                                   database_filepath = DATABASE_FILEPATH)
        self.process = self._execute_command(self.process_cmd,
                                             capture_output = True)
        # --------------------------------------------------------------------

        # --------------------------------------------------------------------
        #   Set up the ZeroMQ context, sockets, and poller.
        # --------------------------------------------------------------------
        self.context = zmq.Context(1)
        self.client = self.context.socket(zmq.REQ)
        self.client.connect(CLIENT_ZEROMQ_BINDING)
        self.poller = zmq.Poller()
        self.poller.register(self.client, zmq.POLLIN)
        self.poll_interval = 1000
        # --------------------------------------------------------------------

    def tearDown(self):
        # --------------------------------------------------------------------
        #   Kill the process.
        # --------------------------------------------------------------------
        assert_not_equal(self.process, None)
        self.process.kill()
        time.sleep(0.5)
        assert_not_equal(self.process.poll(), None)
        # --------------------------------------------------------------------

        # --------------------------------------------------------------------
        #   Clean up the ZeroMQ stuff.
        # --------------------------------------------------------------------
        self.poller.unregister(self.client)
        self.client.close(linger = 0)
        self.context.destroy(linger = 0)
        # --------------------------------------------------------------------

    def _create_basic_message(self):
        rv = {"version": "1.0"}
        return rv

    def send_message(self, message_type, message_args):
        base_message = self._create_basic_message()
        base_message["message_type"] = message_type
        for (key, value) in message_args.items():
            base_message[key] = value
        self.client.send(json.dumps(base_message))

    def get_message(self, timeout = 3*1000):
        start_time = time.time()
        while True:
            if ((time.time() - start_time) * 1000) >= timeout:
                raise TimeoutException
            socks = dict(self.poller.poll(self.poll_interval))
            if socks.get(self.client, None) == zmq.POLLIN:
                return self.handle_message(self.client)

    def handle_message(self, socket):
        message = socket.recv()
        return message

    def test_001_is_runnable(self):
        """ Still running after we launch it.

        As authauth is a persistent server it should be still be running!"""
        time.sleep(1)
        assert_not_equal(self.process, None)
        assert_equal(self.process.poll(), None)

    def test_002_is_pingable(self):
        """ Responds to pings.

        Send a basic 'ping', expect a 'pong' back."""

        message_type = "ping"
        message_args = {}
        self.send_message(message_type, message_args)
        reply = self.get_message()
        assert_not_equal(reply, None)

        reply_decoded = json.loads(reply)

        message_type = reply_decoded.get("message_type", None)
        assert_equal(message_type, "pong")

        message_status = reply_decoded.get("status", None)
        assert_equal(message_status, "ok")

    def test_003_get_user_by_google_email_when_empty_returns_nothing(self):
        """ When database empty getting user by Google email returns nothing."""
        message_type = "get_user"
        message_args = {"user_type": "google",
                        "email": "user@host.com"}
        self.send_message(message_type, message_args)
        reply = self.get_message()
        assert_not_equal(reply, None)
        reply_decoded = json.loads(reply)
        assert_equal(reply_decoded["message_type"], "get_user_response")
        assert_equal(reply_decoded["status"], "ok")
        assert_equal(reply_decoded["user_id"], None)

    def test_004_add_then_get_user_by_google_email(self):
        """ Add a user by Google email, then get it."""
        message_type = "add_user"
        message_args = {"user_type": "google",
                        "email": "user@host.com"}
        self.send_message(message_type, message_args)
        reply = self.get_message()
        assert_not_equal(reply, None)
        reply_decoded = json.loads(reply)
        message_type = reply_decoded.get("message_type", None)
        assert_equal(reply_decoded["message_type"], "add_user_response")
        assert_equal(reply_decoded["status"], "ok")

        message_type = "get_user"
        message_args = {"user_type": "google",
                        "email": "user@host.com"}
        self.send_message(message_type, message_args)
        reply = self.get_message()
        assert_not_equal(reply, None)
        reply_decoded = json.loads(reply)
        assert_equal(reply_decoded["message_type"], "get_user_response")
        assert_equal(reply_decoded["status"], "ok")
        assert_not_equal(reply_decoded["user_id"], None)

