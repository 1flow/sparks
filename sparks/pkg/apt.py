# -*- coding: utf-8 -*-

from ..fabric import QUIET, sudo, exists, with_remote_configuration
from ..fabric.utils import list_or_split
from .common import is_installed, search


# ---------------------------------------------- APT package management

APT_CMD = ("DEBIAN_PRIORITY=critical DEBIAN_FRONTEND=noninteractive "
           "apt-get -o Dpkg::Options::='--force-confold'")


@with_remote_configuration
def apt_usable(remote_configuration=None):

    return remote_configuration.is_deb


def apt_is_installed(pkg):
    """ Return ``True`` if a given package is installed via APT/dpkg. """

    # OMG, this is so ugly. but `dpkg -l %s` will answer
    # 'un <package> uninstalled' + exit 0 if not installed.
    return is_installed('dpkg -l | grep -E "^(ii|rc)  %s "' % pkg)


def apt_update():
    """ Update APT packages list. """

    sudo('apt-get -qq update', quiet=QUIET)


def apt_upgrade():
    """ Upgrade outdated Debian packages. """

    # create a line "force-confold" in `/etc/dpkg/dpkg.cfg`.
    # Or, just:

    sudo(APT_CMD + ' -q -u dist-upgrade --yes --force-yes', quiet=QUIET)


def apt_add(pkgs):
    for pkg in list_or_split(pkgs):
        if not apt_is_installed(pkg):
            sudo(APT_CMD + ' -q install --yes --force-yes %s' % pkg,
                 quiet=QUIET)


def apt_del(pkgs):
    for pkg in list_or_split(pkgs):
        if apt_is_installed(pkg):
            sudo(APT_CMD + ' -q remove --purge --yes --force-yes %s' % pkg,
                 quiet=QUIET)


def ppa(src):

    # This package contains `add-apt-repository`…
    apt_add(('python-software-properties', ))

    sudo('add-apt-repository -y "%s"' % src)
    apt_update()


def key(key):
    """ Add a GPG key to the local APT key database. """

    sudo('wget -q -O - %s | apt-key add -' % key, quiet=QUIET)


def ppa_pkg(src, pkgs, check_path=None):

    if check_path and exists(check_path):
        return

    ppa(src)
    apt_add(pkgs)


def apt_search(pkgs):
    for pkg in list_or_split(pkgs):
        yield search("apt-cache search %s" % pkg)
