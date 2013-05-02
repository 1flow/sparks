# -*- coding: utf8 -*-

import sys
import os
import ast
import logging
import platform
import functools
import cPickle as pickle
import cStringIO as StringIO

from ..foundations.classes import SimpleObject
from ..contrib import lsb_release

from . import nofabric

try:
    from fabric.api              import env
    from fabric.api              import run as fabric_run
    from fabric.api              import sudo as fabric_sudo
    from fabric.api              import local as fabric_local
    from fabric.operations       import get
    from fabric.context_managers import prefix
    from fabric.colors           import cyan

    # imported from utils
    from fabric.contrib.files    import exists # NOQA

    # used in sparks submodules, not directly here. Thus the # NOQA.
    from fabric.api              import task # NOQA
    from fabric.context_managers import cd # NOQA
    from fabric.colors           import green # NOQA

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
LOGGER = logging.getLogger(__name__)
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
        self.verbose     = verbose
        LOGGER.info('>> VERBOSE: %s', self.verbose)

        # No need to `deactivate` for this calls, it's pure shell.
        self.user, self.tilde = run('echo "${USER},${HOME}"',
                                    quiet=True).strip().split(',')

        self.get_platform()
        self.get_uname()
        self.get_virtual_machine()

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

    def __getattr__(self, key):
        """ This lazy getter will allow to load the Django settings after
            Fabric and the project fabfile has initialized `env`. Doing
            elseway leads to cycle dependancy KeyErrors. """

        if key == 'django_settings':
            self.get_django_settings()
            return self.django_settings

    def get_platform(self):
        # Be sure we don't get stuck in a virtualenv for free.
        with prefix('deactivate >/dev/null 2>&1 || true'):
            out = run("python -c 'import lsb_release; "
                      "print lsb_release.get_lsb_information()'",
                      quiet=not self.verbose)

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
                    'cannot determine platform of {0}'.format(self.host_string))

    def get_uname(self):
        # Be sure we don't get stuck in a virtualenv for free.
        with prefix('deactivate >/dev/null 2>&1 || true'):
            out = run("python -c 'import os; print os.uname()'",
                      quiet=not self.verbose)

        self.uname = SimpleObject(from_dict=dict(zip(
                                  ('sysname', 'nodename', 'release',
                                  'version', 'machine'),
                                  ast.literal_eval(out))))

        self.hostname = self.uname.nodename

    def get_virtual_machine(self):
        # TODO: implement me (and under OSX too).
        self.is_vmware = False

        # NOTE: this test could fail in VMs where nothing is mounted from
        # the host. In my own configs, this never occurs, but who knows.
        # TODO: check this works under OSX too, or enhance the test.
        self.is_parallel = run('mount | grep prl_fs', quiet=not self.verbose,
                               warn_only=True).succeeded

        self.is_vm = self.is_parallel or self.is_vmware

    def get_django_settings(self):

        # transform the supervisor syntax to shell syntax.
        env_var1 = ' '.join(env.environment_vars) \
            if hasattr(env, 'environment_vars') else ''

        env_var2 = 'DJANGO_SETTINGS_MODULE="{0}.settings"'.format(env.project)

        # Here, we *NEED* to be in the virtualenv, to get the django code.
        # NOTE: this code is kind of weak, it will fail if settings include
        # complex objects, but we hope it's not.

        prefix_cmd = 'workon {0}'.format(env.virtualenv) \
            if hasattr(env, 'virtualenv') else ''

        pickled_settings = StringIO.StringIO()

        with prefix(prefix_cmd):
            with cd(env.root if hasattr(env, 'root') else ''):
                # NOTE: this doesn't work with “ with open(…) as f: ”, thus
                # I would have greatly prefered this modern version…
                out = run(("{0} {1} python -c 'import cPickle as pickle; "
                          "from django.conf import settings; "
                          "settings._setup(); "
                          "f=open(\"__django_settings__.pickle\", "
                          "\"w\"); pickle.dump(settings._wrapped, f, "
                          "pickle.HIGHEST_PROTOCOL); f.close()'").format(
                          env_var1, env_var2), quiet=not self.verbose,
                          warn_only=True)

                if out.succeeded:
                    get('__django_settings__.pickle',
                        pickled_settings)
                    run('rm -f __django_settings__.pickle',
                        quiet=not self.verbose)

                    try:
                        self.django_settings = pickle.loads(
                            pickled_settings.getvalue())

                    except:
                        LOGGER.exception('Cannot load remote django settings!')

                    pickled_settings.close()


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

        lsb = lsb_release.get_lsb_information()

        if lsb:
            # FIXME: on anything other than Debian/Ubuntu, this will FAIL!
            self.lsb = SimpleObject(
                from_dict=lsb)
            self.is_osx = False

        else:
            self.lsb    = None
            self.is_osx = True
            self.mac    = SimpleObject(from_dict=dict(zip(
                                       ('release', 'version', 'machine'),
                                       platform.mac_ver())))

        self.uname = SimpleObject(from_dict=dict(zip(
                                  ('sysname', 'nodename', 'release',
                                  'version', 'machine'),
                                  os.uname())))

        self.hostname = self.uname.nodename

        self.user, self.tilde = nofabric.local('echo "${USER},${HOME}"',
                                               ).output.strip().split(',')

        # TODO: implement me (and under OSX too).
        self.is_vmware = False

        # NOTE: this test could fail in VMs where nothing is mounted from
        # the host. In my own configs, this never occurs, but who knows.
        # TODO: check this works under OSX too, or enhance the test.
        self.is_parallel = nofabric.local('mount | grep prl_fs').succeeded

        self.is_vm = self.is_parallel or self.is_vmware

    def __getattr__(self, key):
        """ This lazy getter will allow to load the Django settings after
            Fabric and the project fabfile has initialized `env`. Doing
            elseway leads to cycle dependancy KeyErrors. """

        if key == 'django_settings':
            self.get_django_settings()
            return self.django_settings

    def get_django_settings(self):

        # Set the environment exactly how it should be for runserver.
        # Supervisor environment can hold the sparks settings,
        # while Django environment will hold the project settings.

        if hasattr(env, 'environment_vars'):
            for env_var in env.environment_vars:
                name, value = env_var.strip().split('=')
                os.environ[name] = value

        os.environ['DJANGO_SETTINGS_MODULE'] = \
            '{0}.settings'.format(env.project)

        # Insert the $CWD in sys path, and pray for the user to have called
        # `fab` from where `manage.py` is. This is the way it should be done
        # but who knows…
        current_root = os.getcwd()
        sys.path.append(current_root)

        try:
            from django.conf import settings as django_settings
            # Avoid Django to (re-)configure our own logging;
            # the Fabric output becomes a mess without this.
            django_settings._configure_logging = lambda x: None

            django_settings._setup()

        except ImportError:
            raise RuntimeError('Django settings could not be loaded.')

        else:
            self.django_settings = django_settings._wrapped

        finally:
            sys.path.remove(current_root)


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


if local_configuration is None:
    local_configuration = LocalConfiguration()
