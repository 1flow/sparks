# -*- coding: utf-8 -*-
"""

    The official sparks way to handle FreeBSD is PKGng. See below for why.

    Note about FreeBSD ports/packages
    —————————————————————————————————

    As sparks deals with automatic deployment, we choose explicitely to support
    the packaging system (PKGng), not the port system.

    During our implementation, we first supported the port system (via
    portmaster), but this happened to be a deal breaker because of some
    unrecoverable differences between ports names and packages names, and
    the inability to query if one port is installed, because the port name
    doesn't appear “as is” in the list of installed packages.

    For example, installing devel/ruby-gems creates the package ruby19-gems-…
    and the original port name is not present in `portmaster --list-origins`.
    Hence, devel/ruby-gems gets reinstalled at every deployment, which is
    unacceptable. This happened also for PostgreSQL (port name:
    databases/postgresql94-server, pkg name: postgresql9-server-9.4) and
    lang/gcc.

    On the other side, using PKG gives consistent results by using only pkg
    names, eg.:

        sudo pkg install ruby-gems
        […]
        pkg: No packages available to install matching 'ruby-gems' have been found in the repositories

        sudo pkg install ruby19-gems
        Checking integrity... done (0 conflicting)
        The most recent version of packages are already installed

        pkg info | grep ruby19-gems
        ruby19-gems-1.8.29             Package[…]

"""

from ..fabric import sudo, with_remote_configuration, QUIET
from ..fabric.utils import list_or_split
from .common import is_installed, search


# --------------------------------------------- Brew package management


@with_remote_configuration
def pkgng_usable(remote_configuration=None):

    if not remote_configuration.is_freebsd:
        return False

    if not os.path.exists('/usr/local/bin/sudo'):
        LOGGER.error(u'sudo is not installed, sparks PKG management will '
                     u'not work at all. Please install security/sudo before '
                     u'continuing.')
        raise SystemExit(100)

    if not os.path.exists('/usr/local/sbin/pkg'):
        LOGGER.error(u'PKGng is not installed. Sparks package management will '
                     u'not work properly. Please install ports-mgmt/pkg '
                     u'before continuing.')
        raise SystemExit(101)

    return True


def pkgng_is_installed(pkg):
    """ Return ``True`` if a given package is installed. """

    return is_installed("pkg info %s >/dev/null 2>&1" % pkg)


def pkgng_add(pkgs):
    for pkg in list_or_split(pkgs):
        if not pkgng_is_installed(pkg):
            # -U means REPO_AUTOUPDATE=false
            sudo('pkg install -Uy %s' % pkg, quiet=QUIET)


def pkgng_del(pkgs):
    for pkg in list_or_split(pkgs):
        if pkgng_is_installed(pkg):
            sudo('pkg delete -Ryf %s' % pkg, quiet=QUIET)


def pkgng_update():

    sudo('pkg update', quiet=QUIET)


def pkgng_upgrade():

    sudo('pkg upgrade -Uy', quiet=QUIET)


def pkgng_search(pkgs):
    for pkg in list_or_split(pkgs):
        yield search("pkg search -L name %s" % pkg)
