# -*- coding: utf-8 -*-

from ..fabric import sudo, with_remote_configuration
from ..fabric.utils import list_or_split
from .common import is_installed, search


# --------------------------------------------- Brew package management


@with_remote_configuration
def ports_usable(remote_configuration=None):

    if not remote_configuration.is_freebsd:
        return False

    if not os.path.exists('/usr/local/bin/sudo'):
        LOGGER.error(u'sudo is not installed, sparks PKG management will '
                     u'not work at all. Please install security/sudo before '
                     u'continuing.')
        raise SystemExit(1)

    if not os.path.exists('/usr/local/sbin/portmaster'):
        LOGGER.error(u'portmaster is not installed, sparks PKG management will '
                     u'not work properly. Please install ports-mgmt/portmaster '
                     u'before continuing.')
        raise SystemExit(1)

    # Not needed now that we have --list-origins to check installed packages.
    # But keeping it here for memories in case we need it. NOTE: portsearch -u
    # is so long it renders the whole thing unusable…
    #
    #if not os.path.exists('/usr/local/bin/portsearch'):
    #    LOGGER.error(u'portsearch is not installed, sparks PKG management will '
    #                 u'not work properly. Please install ports-mgmt/portsearch '
    #                 u'before continuing.')
    #    raise SystemExit(1)

    return True


def ports_is_installed(pkg):
    """ Return ``True`` if a given port is installed. """

    # Note, some ports (like databases/postgresql94-server) can be checked
    # only via list-origins, because the final package name is different from
    # the port name (eg. postgresql9-server-9.4.b1_1 for pkg name, and
    # databases/postgresql9-server does not exist as port name…).
    # The vast majority of other ports can be checked via “-l”.
    # Thus, we must check both, to avoid reinstalling already installed package
    # as much as we can (reinstalling gcc at each deployment is not an option).

    return is_installed("portmaster --list-origins "
                        "| grep '^%s$' >/dev/null 2>&1" % pkg) \
        or is_installed("portmaster -l "
                        "| grep ' %s$' >/dev/null 2>&1" % pkg)


def ports_add(pkgs):
    for pkg in list_or_split(pkgs):
        if not ports_is_installed(pkg):
            sudo('portmaster --no-confirm -y %s' % pkg)


def ports_del(pkgs):
    for pkg in list_or_split(pkgs):
        if ports_is_installed(pkg):
            sudo('pkg_delete -rf %s' % pkg)


def ports_update():

    sudo('portsnap update')


def ports_upgrade():

    sudo('portmaster --no-confirm -yDa')


def ports_search(pkgs):
    for pkg in list_or_split(pkgs):
        yield search("find /usr/ports -maxdepth 2 -type d -name '*%s*' "
                     "| sed -e 's#/usr/ports/##g'" % pkg)
