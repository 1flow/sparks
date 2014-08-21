# -*- coding: utf-8 -*-

from ..fabric import run, with_remote_configuration
from ..fabric.utils import list_or_split
from .common import is_installed, search


# --------------------------------------------- Brew package management


@with_remote_configuration
def ports_usable(remote_configuration=None):

    return remote_configuration.is_freebsd


def ports_is_installed(pkg):
    """ Return ``True`` if a given port is installed.
    """

    return is_installed('portmaster -l | grep %s >/dev/null 2>&1' % pkg)


def ports_add(pkgs):
    """ Add a local package via ports. """

    for pkg in list_or_split(pkgs):
        if not ports_is_installed(pkg):
            run('portmaster %s' % pkg)


def ports_del(pkgs):
    for pkg in list_or_split(pkgs):
        if ports_is_installed(pkg):
            run('pkg_delete -rf %s' % pkg)


def ports_update():
    """ Update Homebrew formulas. """

    run('portsnap update')


def ports_upgrade():
    """ Upgrade outdated brew packages. """

    run('portmaster -Da')


def ports_search(pkgs):
    for pkg in list_or_split(pkgs):
        yield search("find /usr/ports -maxdepth 2 -type d -name '*%s*' "
                     "| sed -e 's#/usr/ports/##g'" % pkg)
