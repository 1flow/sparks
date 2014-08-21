# -*- coding: utf-8 -*-

from ..fabric import sudo, exists, with_remote_configuration
from ..fabric.utils import list_or_split
from .common import is_installed, search


# ---------------------------------------------- APT package management

ARCH_CMD = "pacman"


@with_remote_configuration
def arch_usable(remote_configuration=None):

    return remote_configuration.lsb and remote_configuration.lsb.ID == 'arch'


def arch_is_installed(pkg):
    """ Return ``True`` if a given package is installed. """

    return is_installed('%s -Qs "%s"' % (ARCH_CMD, pkg))


def arch_update():
    """ Update packages list. """

    sudo('%s -Sy' % ARCH_CMD)


def arch_upgrade():
    """ Upgrade outdated packages. """

    # create a line "force-confold" in `/etc/dpkg/dpkg.cfg`.
    # Or, just:

    sudo('%s -Su --noconfirm --noprogressbar --force' % ARCH_CMD)


def arch_add(pkgs):
    for pkg in list_or_split(pkgs):
        if not arch_is_installed(pkg):
            sudo(ARCH_CMD + ' -S --noconfirm --noprogressbar --force %s' % pkg)


def arch_del(pkgs):
    for pkg in list_or_split(pkgs):
        if arch_is_installed(pkg):
            sudo(ARCH_CMD + ' -Rs --noconfirm --noprogressbar --force %s' % pkg)

def arch_search(pkgs):
    for pkg in list_or_split(pkgs):
        yield search("%s -Ss %s" % (ARCH_CMD, pkg))
