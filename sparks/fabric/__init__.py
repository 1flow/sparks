# -*- coding: utf8 -*-

import os
import ast
import functools
import platform

from ..foundations.classes import SimpleObject

from . import nofabric

try:
    from fabric.api              import run as fabric_run
    from fabric.api              import sudo as fabric_sudo
    from fabric.api              import local as fabric_local
    from fabric.api              import env
    from fabric.contrib.files    import exists
    from fabric.context_managers import prefix
    from fabric.colors           import cyan

    # used in sparks submodules, not directly here. Thus the # NOQA.
    from fabric.api              import task # NOQA
    from fabric.context_managers import cd # NOQA
    from fabric.colors           import green # NOQA

    #from fabric.api              import env
    #if not env.all_hosts:
    #    env.host_string = 'localhost'

    _wrap_fabric = False

    #
    # NOTE: we re-wrap fabric functions into ours, which test against localhost.
    #   This allows multiprocessing to run correctly on localhost, via real
    #   local commands.
    #   Else, paramiko will fail with obscure errors (observed in the `pkgmgr`),
    #   and it's horribly terrible to debug (trust me).
    #   Hoping nobody will try to multiprocessing.Process(fabric) via sparks
    #   (or not). This only seems to work when fabric does the @parallel jobs,
    #   not when trying to run fabric tasks in multiprocessing.* encapsulation.
    #

    def run(*args, **kwargs):
        if is_localhost(env.host_string):
            return nofabric.run(*args, **kwargs)

        else:
            return fabric_run(*args, **kwargs)

    def local(*args, **kwargs):
        if is_localhost(env.host_string):
            return nofabric.local(*args, **kwargs)

        else:
            return fabric_local(*args, **kwargs)

    def sudo(*args, **kwargs):
        if is_localhost(env.host_string):
            return nofabric.sudo(*args, **kwargs)

        else:
            return fabric_sudo(*args, **kwargs)

except ImportError:
    # If fabric is not available, this means we are imported from 1nstall.py,
    # or more generaly fabric is not installed.
    # Everything will fail except the base system detection. We define the bare
    # minimum for it to work on a local Linux/OSX system.

    run   = nofabric.run # NOQA
    local = nofabric.local # NOQA
    sudo  = nofabric.sudo # NOQA

# Global way to turn all of this module silent.
quiet = not bool(os.environ.get('SPARKS_VERBOSE', False))

remote_configuration = None
local_configuration  = None


# =================================================== Remote system information


def is_localhost(hostname):
    return hostname in ('localhost', 'localhost.localdomain',
                        '127.0.0.1', '127.0.1.1', '::1')


class RemoteConfiguration(object):
    """ Define an easy to use object with remote machine configuration. """

    def __init__(self, host_string, verbose=False):

        self.host_string = host_string

        # Be sure we don't get stuck in a virtualenv for free.
        with prefix('deactivate >/dev/null 2>&1 || true'):
            out = run("python -c 'import lsb_release; "
                      "print lsb_release.get_lsb_information()'",
                      quiet=not verbose)

        try:
            self.lsb    = SimpleObject(from_dict=ast.literal_eval(out))
            self.is_osx = False

        except SyntaxError:
            self.lsb    = None
            self.is_osx = True

            # Be sure we don't get stuck in a virtualenv for free.
            with prefix('deactivate >/dev/null 2>&1 || true'):
                out = run("python -c 'import platform; "
                          "print platform.mac_ver()'", quiet=True)
            try:
                self.mac = SimpleObject(from_dict=dict(zip(
                                    ('release', 'version', 'machine'),
                                    ast.literal_eval(out))))
            except SyntaxError:
                # something went very wrong,
                # none of the detection methods worked.
                raise RuntimeError(
                    'cannot determine platform of {0}'.format(host_string))

        # Be sure we don't get stuck in a virtualenv for free.
        with prefix('deactivate >/dev/null 2>&1 || true'):
            out = run("python -c 'import os; print os.uname()'",
                      quiet=not verbose)

        self.uname = SimpleObject(from_dict=dict(zip(
                                  ('sysname', 'nodename', 'release',
                                  'version', 'machine'),
                                  ast.literal_eval(out))))

        #
        # No need to `deactivate` for the next calls, they are pure shell.
        #

        self.user, self.tilde = run('echo "${USER},${HOME}"',
                                    quiet=True).strip().split(',')

        # TODO: implement me (and under OSX too).
        self.is_vmware = False

        # NOTE: this test could fail in VMs where nothing is mounted from
        # the host. In my own configs, this never occurs, but who knows.
        # TODO: check this works under OSX too, or enhance the test.
        self.is_parallel = run('mount | grep prl_fs', quiet=not verbose,
                               warn_only=True).succeeded

        self.is_vm = self.is_parallel or self.is_vmware

        if verbose:
            print('Remote is {release} {host} {vm}{arch}, '
                  '{user} in {home}.'.format(
                  release='Apple OSX {0}'.format(self.mac.release)
                  if self.is_osx
                  else self.lsb.DESCRIPTION,
                  host=cyan(self.uname.nodename),
                  vm=('VMWare ' if self.is_vmware else 'Parallels ')
                  if self.is_vm else '',
                  arch=self.uname.machine,
                  user=cyan(self.user),
                  home=self.tilde,
                  ))


class LocalConfiguration(object):
    """ Define an easy to use object with local machine configuration.

        This class doesn't use fabric, it's used to bootstrap the local
        machine when it's empty and doesn't have fabric installed yet.

        .. warning:: this class won't probably play well in a virtualenv.
            Unlike the :class:`RemoteConfiguration` class, I don't think
            it's pertinent and wanted to :program:`deactivate` first.
     """
    def __init__(self, host_string=None):

        self.host_string = host_string or 'localhost'

        try:
            import lsb_release
            self.lsb    = SimpleObject(
                from_dict=lsb_release.get_lsb_information())
            self.is_osx = False

        except ImportError:
            self.lsb    = None
            self.is_osx = True
            self.mac    = SimpleObject(from_dict=dict(zip(
                                       ('release', 'version', 'machine'),
                                       platform.mac_ver())))

        self.uname = SimpleObject(from_dict=dict(zip(
                                  ('sysname', 'nodename', 'release',
                                  'version', 'machine'),
                                  os.uname())))

        self.user, self.tilde = nofabric.local('echo "${USER},${HOME}"',
                                               ).output.strip().split(',')

        # TODO: implement me (and under OSX too).
        self.is_vmware = False

        # NOTE: this test could fail in VMs where nothing is mounted from
        # the host. In my own configs, this never occurs, but who knows.
        # TODO: check this works under OSX too, or enhance the test.
        self.is_parallel = nofabric.local('mount | grep prl_fs').succeeded

        self.is_vm = self.is_parallel or self.is_vmware


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


# ======================================================================= Utils


def list_or_split(pkgs):
    try:
        return (p for p in pkgs.split() if p not in ('', None, ))

    except AttributeError:
        #if type(pkgs) in (types.TupleType, types.ListType):
        return pkgs


def dsh_to_roledefs():
    dsh_group = os.path.expanduser('~/.dsh/group')
    roles     = {}

    if os.path.exists(dsh_group):
        for entry in os.listdir(dsh_group):
            if entry.startswith('.'):
                continue

            fullname = os.path.join(dsh_group, entry)

            if os.path.isfile(fullname):
                roles[entry] = [line for line
                                in open(fullname).read().split()
                                if line != '']

    return roles


def symlink(source, destination, overwrite=False, locally=False):

    rm_prefix = ''

    if exists(destination):
        if overwrite:
            rm_prefix = 'rm -rf "%s"; ' % destination

        else:
            return

    command = '%s ln -sf "%s" "%s"' % (rm_prefix, source, destination)

    local(command) if locally else run(command)


# ========================================================== User configuration


@with_remote_configuration
def tilde(directory=None, remote_configuration=None):
    """ Just a handy shortcut. """

    return os.path.join(remote_configuration.tilde, directory or '')


def dotfiles(filename):
    """ Where are my dotfiles? (relative from $HOME).

        .. note:: use with :func:`tilde` to get full path.
            Eg. ``tilde(dotfiles('dot.bashrc'))`` =>
            ``/home/olive/Dropbox/dotfiles/dot.bashrc``.
    """

    return os.path.join('Dropbox/configuration/dotfiles', filename)


if local_configuration is None:
    local_configuration = LocalConfiguration()
