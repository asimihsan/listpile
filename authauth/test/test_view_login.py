#!/usr/bin/env python2.7

# ---------------------------------------------------------------------------
# Copyright (c) 2012 Asim Ihsan (asim dot ihsan at gmail dot com)
# Distributed under the MIT/X11 software license, see the accompanying
# file license.txt or http://www.opensource.org/licenses/mit-license.php.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
#   test_view_login.py. Check that the authauth view supports authentication
#   using Google, Facebook, Twitter, and BrowserID, and then redirects
#   on success to a particular URL.
# ---------------------------------------------------------------------------

# watchmedo shell-command --patterns="*.py" --recursive --command="clear; date; pgrep nosetests; if [[ \`pgrep nosetests\` == '' ]]; tn nosetests --no-skip --detailed-errors --stop --verbosity=2 --logging-filter=authauth --tests=test/; fi"

import os
import sys
import zmq
import subprocess
from string import Template
import time
import json
import uuid
import datetime
import shutil

from nose.tools import raises, assert_false, assert_true, assert_not_equal, assert_equal, assert_less
from nose.plugins.skip import SkipTest, Skip
import unittest

# ---------------------------------------------------------------------------
#   Constants.
# ---------------------------------------------------------------------------
code_filepath = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, "src"))
assert(os.path.isdir(code_filepath))
script_under_test = os.path.join(code_filepath, "authauth_view_start_server.py")
assert(os.path.isfile(script_under_test))

CMD_TEMPLATE = Template(""" ${executable} --test=1 """)

test_filepath = os.path.abspath(os.path.join(__file__, os.pardir))
assert(os.path.isdir(test_filepath))
CASPERJS_CMD_TEMPLATE = Template(""" casperjs --cookies-file=${cookies_filepath} ${script_filepath} """)
LOGIN_GOOGLE_SCRIPT = os.path.join(test_filepath, "test_view_login_google.coffee")
assert(os.path.isfile(LOGIN_GOOGLE_SCRIPT))
LOGIN_GOOGLE_OUTPUT = os.path.join(test_filepath, "test_view_login_google_output")

cookies_filepath = os.path.join(test_filepath, "cookies.txt")
# ---------------------------------------------------------------------------

class TimeoutException(Exception):
    pass

class TestBasic(unittest.TestCase):
    def _execute_command(self,
                         command,
                         capture_output = False,
                         send_output_to_console = False):
        devnull = open(os.devnull, "rb+")
        if capture_output:
            stdout_handle = subprocess.PIPE
        elif send_output_to_console:
            stdout_handle = None
        else:
            stdout_handle = devnull
        process = subprocess.Popen(command,
                                   shell = True,
                                   stdin = devnull,
                                   stdout = stdout_handle)
        return process

    def _kill_process(self, process):
        assert_not_equal(process, None)
        if process.poll() is None:
            process.kill()
        time.sleep(0.5)
        assert_not_equal(process.poll(), None)

    def _start_process(self,
                       cmd,
                       capture_output = False,
                       send_output_to_console = False):
        rv = self._execute_command(cmd,
                                   capture_output,
                                   send_output_to_console)
        return rv

    def setUp(self):
        # --------------------------------------------------------------------
        #   Launch the authauth view process.
        # --------------------------------------------------------------------
        process_cmd = CMD_TEMPLATE.substitute(executable = script_under_test)
        self.process = self._start_process(process_cmd, send_output_to_console = True)
        # --------------------------------------------------------------------

        # --------------------------------------------------------------------
        #   Delete the cookies file before casperjs runs.
        # --------------------------------------------------------------------
        if os.path.isfile(cookies_filepath):
            os.remove(cookies_filepath)
        # --------------------------------------------------------------------

    def tearDown(self):
        self._kill_process(self.process)

    def test_001_login_google(self):
        if os.path.isdir(LOGIN_GOOGLE_OUTPUT):
            shutil.rmtree(LOGIN_GOOGLE_OUTPUT)
        cmd = CASPERJS_CMD_TEMPLATE.substitute(script_filepath = LOGIN_GOOGLE_SCRIPT,
                                               cookies_filepath = cookies_filepath)
        process = self._start_process(cmd, send_output_to_console = True)
        start = datetime.datetime.now()
        end = start + datetime.timedelta(seconds = 120)
        while process.poll() is None:
            time.sleep(1)
            assert_less(datetime.datetime.now(), end, "test timed out")
        self._kill_process(process)
        assert_equal(process.poll(), 0)

