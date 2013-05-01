# -*- coding: utf-8 -*-

from ..fabric import run, with_remote_configuration
from ..fabric.utils import list_or_split
from .common import is_installed, search


# --------------------------------------------- Brew package management


@with_remote_configuration
def brew_usable(remote_configuration=None):

    return remote_configuration.is_osx


def brew_is_installed(pkg):
    """ Return ``True`` if a given application is installed via Brew (on OSX).
    """

    return is_installed('brew list %s >/dev/null 2>&1' % pkg)


def brew_add(pkgs):
    """ Add a local package via Homebrew (on OSX).

        .. note:: we always use FORCE_UNSAFE_CONFIGURE=1 to avoid errors::

            checking whether mknod can create fifo without root privileges...
             configure: error: in `/private/tmp/coreutils-zCgv/coreutils-8.21':
            configure: error: you should not run configure as root (set
                FORCE_UNSAFE_CONFIGURE=1 in environment to bypass this check)
            See `config.log' for more details
            READ THIS: https://github.com/mxcl/homebrew/wiki/troubleshooting
    """

    for pkg in list_or_split(pkgs):
        if not brew_is_installed(pkg):
            run('FORCE_UNSAFE_CONFIGURE=1 brew install %s' % pkg)


def brew_del(pkgs):
    for pkg in list_or_split(pkgs):
        if brew_is_installed(pkg):
            run('brew remove %s' % pkg)


def brew_update():
    """ Update Homebrew formulas. """

    run('brew update')


def brew_upgrade():
    """ Upgrade outdated brew packages. """

    run('brew upgrade')


def brew_search(pkgs):
    for pkg in list_or_split(pkgs):
        yield search("brew search %s 2>&1 | grep -v 'No formula found for' "
                     "| tr ' ' '\n' | sort -u" % pkg)
