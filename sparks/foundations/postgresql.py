# -*- coding: utf-8 -*-
"""
    Fabric common rules for a Django project.

"""

import os
import pwd
import logging
from fabric.api import env
from ..django import is_local_environment
from ..fabric import with_remote_configuration

LOGGER = logging.getLogger(__name__)

BASE_CMD    = 'psql template1 -tc "{0}"'

SELECT_USER = BASE_CMD.format("SELECT usename from pg_user "
                              "WHERE usename = '{user}';")
CREATE_USER = BASE_CMD.format("CREATE USER {user} "
                              "WITH PASSWORD '{password}';")
ALTER_USER  = BASE_CMD.format("ALTER USER {user} "
                              "WITH ENCRYPTED PASSWORD '{password}';")
SELECT_DB   = BASE_CMD.format("SELECT datname FROM pg_database "
                              "WHERE datname = '{db}';")
CREATE_DB   = BASE_CMD.format("CREATE DATABASE {db} OWNER {user};")


@with_remote_configuration
def get_admin_user(remote_configuration=None):

    environ_user = os.environ.get('SPARKS_PG_USER', None)

    if environ_user is not None:
        return environ_user

    if remote_configuration.is_osx:
        if is_local_environment():
            return pwd.getpwuid(os.getuid()).pw_name

        else:
            raise NotImplementedError("Don't know how to find PG user "
                                      "on remote OSX server.")
    elif remote_configuration.lsb:
        # FIXED: on Ubuntu / Debian, it's been `postgres` since ages.
        return 'postgres'

    else:
        raise NotImplementedError("Which kind of remote sytem is this??")


def temper_db_args(db, user, password):
    """ Try to accomodate with DB creation arguments. """

    if hasattr(env, 'settings'):
        if db is not None or user is not None or password is not None:
            LOGGER.warning('Arguments are overridden by Django settings!')

        db       = env.settings.DATABASES['default']['NAME']
        user     = env.settings.DATABASES['default']['USER']
        password = env.settings.DATABASES['default']['PASSWORD']

    else:
        if db is None:
            if user is None:
                raise ValueError('Parameters db and user '
                                 'cannot be None together.')

            db = user

        else:
            if user is None:
                user = db

        if password is None:
            if not is_local_environment():
                raise ValueError('Refusing to set password as username '
                                 'in a real/production environment.')

            password = user

    return db, user, password
