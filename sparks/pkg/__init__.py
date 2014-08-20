# -*- coding: utf-8 -*-

from ..fabric import with_remote_configuration, task

from .pip import (pip_perms,
                  pip2_usable, pip2_is_installed, pip2_add, pip2_search,
                  pip3_usable, pip3_is_installed, pip3_add, pip3_search, )

from .apt import (apt_usable, apt_is_installed, apt_update, apt_upgrade,
                  apt_add, apt_del, apt_search, )

from .arch import (arch_usable, arch_is_installed, arch_update, arch_upgrade,
                  arch_add, arch_del, arch_search, )

from .brew import (brew_usable, brew_is_installed, brew_add, brew_del,
                   brew_update, brew_upgrade, brew_search, )

from .other import (npm_is_installed, npm_add, npm_search,
                    gem_is_installed, gem_add, gem_search, )


# ------------------------------------------ Generic package management


@with_remote_configuration
def pkg_is_installed(pkg, remote_configuration=None):
    if remote_configuration.lsb:
        if remote_configuration.is_arch:
            return arch_is_installed(pkg)

        return apt_is_installed(pkg)
    else:
        return brew_is_installed(pkg)


@with_remote_configuration
def pkg_add(pkgs, remote_configuration=None):
    if remote_configuration.lsb:
        if remote_configuration.is_arch:
            return arch_add(pkg)

        return apt_add(pkgs)
    else:
        return brew_add(pkgs)


@with_remote_configuration
def pkg_del(pkgs, remote_configuration=None):
    if remote_configuration.lsb:
        if remote_configuration.is_arch:
            return arch_del(pkg)

        return apt_del(pkgs)
    else:
        return brew_del(pkgs)


@with_remote_configuration
def pkg_update(remote_configuration=None):
    if remote_configuration.lsb:
        if remote_configuration.is_arch:
            return arch_update(pkg)

        return apt_update()
    else:
        return brew_update()


@with_remote_configuration
def pkg_upgrade(remote_configuration=None):
    if remote_configuration.lsb:
        if remote_configuration.is_arch:
            return arch_upgrade(pkg)

        return apt_upgrade()
    else:
        return brew_upgrade()


# ============================================= Global package upgrades


@task
@with_remote_configuration
def update(remote_configuration=None):
    """ Refresh all package management tools data (packages lists, receipes…).
    """

    # TODO:
    #pip2_update()
    #pip3_update()
    #npm_update()
    #gem_update()

    if remote_configuration.lsb:
        apt_update()
    else:
        brew_update()


@task
@with_remote_configuration
def upgrade(update=False, remote_configuration=None):
    """ Upgrade all outdated packages from all pkg management tools at once. """

    # TODO:
    #pip2_upgrade()
    #pip3_upgrade()
    #npm_upgrade()
    #gem_update()

    if remote_configuration.lsb:
        apt_upgrade()
    else:
        brew_upgrade()
