# -*- coding: utf-8 -*-

from ..fabric import sudo


# ========================================== Package management helpers


def silent_sudo(command):

    return sudo(command, quiet=True, warn_only=True)


def is_installed(test_installed_command):
    """ Return ``True`` if :param:`test_installed_command` succeeded. """

    return silent_sudo(test_installed_command).succeeded


def search(search_command):

    return sudo(search_command, quiet=True)
