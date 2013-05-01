# -*- coding: utf8 -*-

import os
import functools

from .utils import env, LocalConfiguration, RemoteConfiguration, is_localhost

# Some other package expect to find them here.
from .utils import dsh_to_roledefs, symlink, tilde, dotfiles # NOQA

# Global way to turn all of this module silent.
quiet = not bool(os.environ.get('SPARKS_VERBOSE', False))

remote_configuration = None
local_configuration  = None


def with_remote_configuration(func):

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        global remote_configuration
        if remote_configuration is None:
            remote_configuration = find_configuration_type(env.host_string)

        elif remote_configuration.host_string != env.host_string:
            # host changed: fabric is running the same task on another host.
            remote_configuration = find_configuration_type(env.host_string)

        return func(*args, remote_configuration=remote_configuration, **kwargs)

    return wrapped


def with_local_configuration(func):

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        global local_configuration
        if local_configuration is None:
            local_configuration = LocalConfiguration()

        return func(*args, local_configuration=local_configuration, **kwargs)

    return wrapped


def find_configuration_type(hostname):

    if is_localhost(hostname):
        return LocalConfiguration()

    else:
        return RemoteConfiguration(hostname, verbose=not quiet)


if local_configuration is None:
    local_configuration = LocalConfiguration()
