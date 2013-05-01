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

BASE_CMD    = 'psql {connect} template1 -tc "{sqlcmd}"'

# {connect} is intentionnaly repeated, it will be filled later.
# Without repeating it, `.format()` will fail with `KeyError`.
SELECT_USER = BASE_CMD.format(connect='{connect}',
                              sqlcmd="SELECT usename from pg_user "
                              "WHERE usename = '{user}';")
CREATE_USER = BASE_CMD.format(connect='{connect}',
                              sqlcmd="CREATE USER {user} "
                              "WITH PASSWORD '{password}';")
ALTER_USER  = BASE_CMD.format(connect='{connect}',
                              sqlcmd="ALTER USER {user} "
                              "WITH ENCRYPTED PASSWORD '{password}';")
SELECT_DB   = BASE_CMD.format(connect='{connect}',
                              sqlcmd="SELECT datname FROM pg_database "
                              "WHERE datname = '{db}';")
CREATE_DB   = BASE_CMD.format(connect='{connect}',
                              sqlcmd="CREATE DATABASE {db} OWNER {user};")


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

    if db is None and user is None and password is None:
        if hasattr(env, 'settings'):
            # if django settings has 'test' or 'production' DB,
            # get it, else get 'default' because all settings have it.
            db_settings = env.settings.DATABASES.get(
                env.environment, env.settings.DATABASES['default'])

            db       = db_settings['NAME']
            user     = db_settings['USER']
            password = db_settings['PASSWORD']

        else:
            raise ValueError('No database parameters supplied '
                             'and no Django settings available!')

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
