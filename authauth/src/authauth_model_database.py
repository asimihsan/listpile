#!/usr/bin/env python2.7

# ---------------------------------------------------------------------------
# Copyright (c) 2012 Asim Ihsan (asim dot ihsan at gmail dot com)
# Distributed under the MIT/X11 software license, see the accompanying
# file license.txt or http://www.opensource.org/licenses/mit-license.php.
# ---------------------------------------------------------------------------

import os
import sys
import apsw
import uuid

import logging
APP_NAME = "authauth_model.db"
logger = logging.getLogger(APP_NAME)

class GoogleUser(object):
    keys = ["email",
            "user_id",
            "first_name",
            "last_name",
            "name",
            "locale"]
    def __init__(self,
                 email,
                 user_id,
                 first_name = None,
                 last_name = None,
                 name = None,
                 locale = None):
        self.email = email
        self.user_id = user_id
        self.first_name = first_name
        self.last_name = last_name
        self.name = name
        self.locale = locale

    def __str__(self):
        items = [(key, getattr(self, key)) for key in self.keys]
        item_repr = ", ".join(["%s=%s" % (key, value) for (key, value) in items])
        return "{GoogleUser: %s}" % (item_repr)

class Database(object):
    # ----------------------------------------------------------------------
    # Tables.
    # ----------------------------------------------------------------------
    # Role
    DROP_ROLE_TABLE = """DROP TABLE IF EXISTS role;"""
    CREATE_ROLE_TABLE = """CREATE TABLE role (
        role_id TEXT PRIMARY KEY,
        role_name TEXT NOT NULL,
        privileges TEXT);"""

    # User
    DROP_USER_TABLE = """DROP TABLE IF EXISTS user;"""
    CREATE_USER_TABLE = """CREATE TABLE user (
        user_id TEXT PRIMARY KEY,
        role_id TEXT NOT NULL);"""

    # Google authentication details
    DROP_AUTH_GOOGLE_TABLE = """DROP TABLE IF EXISTS auth_google;"""
    CREATE_AUTH_GOOGLE_TABLE = """CREATE TABLE auth_google (
        email TEXT PRIMARY KEY,
        user_id TEXT UNIQUE NOT NULL,
        first_name TEXT,
        last_name TEXT,
        name TEXT,
        locale TEXT);"""

    INSERT_STATEMENTS = [ \
                         DROP_ROLE_TABLE,
                         CREATE_ROLE_TABLE,
                         DROP_USER_TABLE,
                         CREATE_USER_TABLE,
                         DROP_AUTH_GOOGLE_TABLE,
                         CREATE_AUTH_GOOGLE_TABLE,
                         #DROP_AUTH_FACEBOOK_TABLE,
                         #CREATE_AUTH_FACEBOOK_TABLE,
                         #DROP_AUTH_TWITTER_TABLE,
                         #CREATE_AUTH_TWITTER_TABLE,
                         #DROP_AUTH_BROWSERID_TABLE,
                         #CREATE_AUTH_BROWSERID_TABLE,
                         #DROP_AUTH_API_TABLE,
                         #CREATE_AUTH_API_TABLE,
                         #DROP_LIST_TABLE,
                         #CREATE_LIST_TABLE,
                        ]

    # ----------------------------------------------------------------------
    # Indexes.
    # ----------------------------------------------------------------------
    INDEX_USER_ID_ON_AUTH_GOOGLE = """CREATE INDEX user_id_on_auth_google on auth_google(user_id);"""
    #INDEX_LIST_ID_ON_LIST = """CREATE INDEX list_id_on_list on list(list_id);"""
    INDEX_STATEMENTS = [ \
                        INDEX_USER_ID_ON_AUTH_GOOGLE,
                        #INDEX_LIST_ID_ON_LIST,
                       ]
    # ----------------------------------------------------------------------

    # ----------------------------------------------------------------------
    # Foreign key constraints.
    # ----------------------------------------------------------------------
    FOREIGN_KEY_STATEMENTS = []
    # ----------------------------------------------------------------------

    ALL_STATEMENTS = INSERT_STATEMENTS + INDEX_STATEMENTS + FOREIGN_KEY_STATEMENTS

    # ------------------------------------------------------------------------
    #   Database statements related to user authentication and CRUD.
    # ------------------------------------------------------------------------
    GET_USER_ID_FROM_GOOGLE_EMAIL = """SELECT user_id FROM auth_google WHERE email = ?;"""
    CREATE_AUTH_GOOGLE = """INSERT INTO auth_google (email, user_id, first_name, last_name, name, locale) VALUES (?, ?, ?, ?, ?, ?);"""

    def __init__(self, filepath, empty_database = False):
        self.filepath = filepath
        if empty_database:
            self.empty_database()
        self.connection = apsw.Connection(self.filepath)
        if empty_database:
            self.create_tables()

    def empty_database(self):
        with open(self.filepath, "wb") as f:
            pass

    def create_tables(self):
        for statement in self.ALL_STATEMENTS:
            self.execute_statement(statement, ())

    def execute_statement(self, statement, args):
        logger = logging.getLogger("%s.execute_statement" % (APP_NAME, ))
        logger.debug("entry. statement: %s, args: %s" % (statement, args))
        cursor = self.connection.cursor()
        return cursor.execute(statement, args)

    def get_google_user(self, email):
        logger = logging.getLogger("%s.get_google_user" % (APP_NAME, ))
        cursor = self.execute_statement(self.GET_USER_ID_FROM_GOOGLE_EMAIL,
                                        (email, ))
        rows = cursor.fetchall()
        if len(rows) == 0:
            user = None
        else:
            assert(len(rows) == 1)
            row = rows[0]
            user_id = row[0]
            logger.debug("user_id: %s" % (user_id, ))
            user = GoogleUser(user_id = user_id,
                              email = email)
        logger.debug("get_google_user returning: %s" % (user, ))
        return user

    def add_google_user(self,
                        email,
                        **kwds):
        logger = logging.getLogger("%s.add_google_user" % (APP_NAME, ))
        user_id = uuid.uuid4().hex
        first_name = kwds.get("first_name", None)
        last_name = kwds.get("last_name", None)
        name = kwds.get("name", None)
        locale = kwds.get("locale", None)
        cursor = self.execute_statement(self.CREATE_AUTH_GOOGLE,
                                        (email,
                                         user_id,
                                         first_name,
                                         last_name,
                                         name,
                                         locale))
        user = GoogleUser(email = email,
                          user_id = user_id,
                          first_name = first_name,
                          last_name = last_name,
                          name = name,
                          locale = locale)
        return user

