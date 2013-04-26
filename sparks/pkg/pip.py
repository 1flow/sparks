# -*- coding: utf-8 -*-

from ..fabric import (task, sudo, list_or_split,
                      quiet, green, run, cd, )
from .common import silent_sudo, is_installed, search


# ---------------------------------------------- PIP package management


@task
def pip_perms(verbose=True):
    """ Apply correct permissions on /usr/local/lib/*. Thanks PIP :-/ """

    if verbose and not quiet:
        print(green('Restoring correct permissions in /usr/local/lib…'))

    silent_sudo('find /usr/local/lib -type f -print0 '
                '| xargs -0 -n 1024 chmod u+rw,g+r,o+r')
    silent_sudo('find /usr/local/lib -type d -print0 '
                '| xargs -0 -n 1024 chmod u+rwx,g+rx,o+rx')


def __pip_find_executable_internal(executable_names=None):

    if executable_names is None:
        raise ValueError('Must provide PIP executable names as list or tuple!')

    # run() hangs the 3rd time when called from `contrib/pkgmgr.py`.
    #print('lookup pip3 in %s' % remote_configuration)

    for pip_exec in executable_names:
        if run('which %s' % pip_exec, quiet=True, warn_only=True).succeeded:
            return pip_exec

    return None


def __pip_is_installed_internal(pkg, py3=False):
    """ Return ``True`` if a given Python module is installed via PIP. """

    if py3:
        pip = pip3_find_executable()
    else:
        pip = 'pip'

    return is_installed("%s freeze | grep -i '%s=='" % (pip, pkg))


def __pip_add_internal(pkgs, py3=False):

    if py3:
        pip = pip3_find_executable()
    else:
        pip = 'pip'

    # Go to a neutral location before PIP tries to "mkdir build"
    # WARNING: this could be vulnerable to symlink attack when we
    # force unlink of hard-coded build/, but in this case PIP is
    # vulnerable during the install phase too :-/
    with cd('/var/tmp'):
        installed = False
        for pkg in list_or_split(pkgs):
            if not __pip_is_installed_internal(pkg, py3=py3):
                sudo("%s install -U %s " % (pip, pkg))
                installed = True

        if installed:
            silent_sudo('rm -rf build')
            pip_perms()


def __pip_search_internal(pkgs, py3=False):

    if py3:
        pip = pip3_find_executable()
    else:
        pip = 'pip'

    for pkg in list_or_split(pkgs):
        yield search("%s search %s" % (pip, pkg))


# -------------------------------------- PIP2 / PIP3 package management


def pip2_find_executable():

    return __pip_find_executable_internal(executable_names=('pip', 'pip-2.7',
                                          'pip-2', ))


def pip2_usable():

    return pip2_find_executable() is not None


def pip2_is_installed(pkg):

    return __pip_is_installed_internal(pkg)


def pip2_add(pkgs):

    return __pip_add_internal(pkgs)


def pip2_search(pkgs):

    return __pip_search_internal(pkgs)


def pip3_find_executable():
    return __pip_find_executable_internal(executable_names=('pip3', 'pip-3.5',
                                          'pip-3.4', 'pip-3.3', 'pip-3.2', ))


def pip3_usable():

    return pip3_find_executable() is not None


def pip3_is_installed(pkg):

    return __pip_is_installed_internal(pkg, py3=True)


def pip3_add(pkgs):

    return __pip_add_internal(pkgs, py3=True)


def pip3_search(pkgs):

    return __pip_search_internal(pkgs, py3=True)
