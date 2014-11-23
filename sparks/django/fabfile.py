# -*- coding: utf-8 -*-
u"""
Fabric common rules for a Django project.

Handles deployment and service installation / run via supervisor.

Supported roles names:

- ``web``: a gunicorn web server,
- ``worker``: a simple celery worker that operate on the default queue,
- ``worker_{low,medium,high}``: a combination
  of two or three celery workers (can be combined with
  simple ``worker`` too, for fine grained scheduling on
  small architectures),
- ``worker_{io,net,…}`` and all their ``_{low,medium,high}`` variants:
  same idea as above, but with even more fine-graining to suit your need.
- ``worker_{solo,duo,trio,swarm}`` and their ``_{low,medium,high}``
  variants: do you get the idea? All these worker classes are completely
  configurable in terms of concurrency and max-tasks-per-child.
- ``flower``: a flower (celery monitoring) service,
- ``beat``: the Celery **beat** service,
- ``shell``: an iPython notebooks shell service (on 127.0.0.1; up to
  you to get access to it via an SSH tunnel),

For more information, jump to :class:`DjangoTask` and see ``all_roles``
definition in :file:`sparks/fabric/__init__.py`.

"""

import os
import pwd
import logging
import datetime

try:
    from fabric.api import (env, run, sudo, task,
                            local, execute, serial)
    from fabric.tasks import Task
    from fabric.operations import put, prompt
    from fabric.contrib.files import exists, upload_template, sed
    from fabric.context_managers import cd, prefix, settings

except ImportError:
    print('>>> FABRIC IS NOT INSTALLED !!!')
    raise

from ..fabric import (fabfile, all_roles, worker_roles,
                      with_remote_configuration,
                      local_configuration as platform,
                      is_localhost,
                      is_local_environment,
                      is_development_environment,
                      is_production_environment,
                      execute_or_not, get_current_role,
                      worker_information_from_role, QUIET)
from sparks import pkg
from ..foundations import postgresql as pg
from ..foundations.classes import SimpleObject

# Use this in case paramiko seems to go crazy. Trust me, it can do, especially
# when using the multiprocessing module.
#
# logging.basicConfig(format=
#                     '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#                     level=logging.INFO)

LOGGER = logging.getLogger(__name__)


# These can be overridden in local projects fabfiles.
env.requirements_dir      = 'config'
env.requirements_file     = os.path.join(env.requirements_dir,
                                         'requirements.txt')
env.gem_file              = os.path.join(env.requirements_dir,
                                         'Gemfile')
env.dev_requirements_file = os.path.join(env.requirements_dir,
                                         'dev-requirements.txt')
env.branch                = '<GIT-FLOW-DEPENDANT>'
env.use_ssh_config        = True


# ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Django task


class DjangoTask(Task):

    u""" A Simple task wrapper.

    It will ensure you are running your sparks
    Django tasks from near your :file:`manage.py`. This ensures that
    paths are always correctly set, which is too difficult to ensure
    otherwise.

    Sparks Django tasks assume the following project structure:

        $repository_root/
            config/
                *requirements.txt
            $django_project_root/
                settings/                 # or settings.py, to your liking.
                $django_app1/
                …
            manage.py
            fabfile.py
            Procfile.*

    .. versionadded:: in sparks 1.16.2. This is odd and doesn't conform
        to `Semantic Versioning  <http://semver.org/>`_. Sorry for that,
        it should have had. Next time it will do a better job.
    """

    def __init__(self, func, *args, **kwargs):
        super(DjangoTask, self).__init__(*args, **kwargs)
        self.func = func

    def __call__(self, *args, **kwargs):
        if not os.path.exists('./manage.py'):
            raise RuntimeError('You must run this task from where manage.py '
                               'is located, and this must be exactly in ../ '
                               'from your django project.')
        return self.func(*args, **kwargs)

    def run(self, *args, **kwargs):
        return self(*args, **kwargs)


class ServiceRunner(SimpleObject):
    """ Handle all the supervisor/upstart configuration and the
        restart/reload dirty work.

        .. versionchanged:: in 3.0, this class was renamed
            from ``SupervisorHelper`` to ``ServiceRunner`` with the
            added :program:`upstart` support.

        .. versionadded:: in sparks 2.0, all ``supervisor_*`` functions
            were merged into this controller, and support for Fabric's
            ``env.role`` was added.

    """

    nice_defaults = {
        'shell': '-n -7',
        'flower': '-n 10',
        'web': '-n -5',
    }

    ionice_defaults = {
        'shell': '-c 2 -n 2',
        'flower': '-c 3',
    }

    def __init__(self, *args, **kwargs):
        # Too bad, SimpleObject is an old-style class (and must stay)
        SimpleObject.__init__(self, *args, **kwargs)

        self.update  = False
        self.restart = False

        if exists('/usr/bin/supervisorctl'):
            # testing exists('/etc/supervisor') isn't accurate: the
            # directory could still be there on a Debian/Ubuntu system,
            # even after a "remove --purge" (observed on obi.1flow.io).
            self.service_handler = 'supervisor'
        else:
            self.service_handler = 'upstart'

    @classmethod
    def build_program_name(cls, service=None):
        """ Returns a tuple: a boolean and a program name.

            The boolean indicates if the fabric `env` has
            the :attr:`sparks_djsettings` attribute. The program name
            will be somewhat unique, built from ``service``, ``env.project``,
            ``env.sparks_djsettings`` if it exists and ``env.environment``.

            :param service: a string describing the service.
                Defaults to Fabric's ``env.host_string.role`` (which is
                a sparks specific attributes, not yet merged into Fabric
                as os 2013-06) or ``env.sparks_current_role`` which is
                obviously sparks specific too, and exists when only the
                ``-H`` argument is given on command line.
                Can be anything meaningfull, eg. ``worker``, ``db``, etc.

        """

        role_name = get_current_role()

        if role_name is None:
            # This shouldn't happen, in fact. Either Fabric should have
            # set the first, or sparks' execute_or_not() the second.
            raise RuntimeError('WE HAVE NO ROLE, THIS IS MANDATORY.')

        if service is None:
            service = role_name

        # We need something more unique than project, in case we have
        # many environments on the same remote machine. And alternative
        # settings, too, because we will have a supervisor process for them.
        if hasattr(env, 'sparks_djsettings'):
            return True, '{0}_{1}_{2}_{3}'.format(service,
                                                  env.project,
                                                  env.sparks_djsettings,
                                                  env.environment)

        else:
            return False, '{0}_{1}_{2}'.format(service,
                                               env.project,
                                               env.environment)

    def add_environment_to_context(self, context, has_djsettings):
        """ Helper method: add (or not) an ``environment`` item
            to :param:`context`, given the current Fabric ``env``.

            If :param:`has_djsettings` is ``True``, ``SPARKS_DJANGO_SETTINGS``
            will be added.

            If ``env`` has an ``environment_vars`` attributes, they are assumed
            to be a python list (eg.``[ 'KEY1=value', 'KEY2=value2' ]``) and
            will be inserted into context too, converted to supervisor
            configuration file format.
        """

        env_vars = []

        if has_djsettings:
            env_vars.append(sparks_djsettings_env_var().strip())

        if hasattr(env, 'environment_vars'):
                env_vars.extend(env.environment_vars)

        if env_vars:
            context['environment'] = 'environment={0}'.format(
                ','.join(env_vars))

        else:
            # The item must exist, else the templating
            # engine will raise an error. Too bad.
            context['environment'] = ''

    def add_command_pre_post_to_context(self, context, has_djsettings):
        """ This method is called during the context build and before
            supervisor template rendering. It will set the context variables
            ``command_pre_args`` and ``command_post_args`` to empty values
            in the first time. Then it will call the
            method ``self.custom_context_handler()`` if it exists, passing
            a copy of the current context, a ``has_djsettings`` boolean and
            and the ``remote_configuration`` to it, in case handler needs to
            inspect current values. The custom handler should return the
            context copy, with ``command_{pre,post}_args`` modified to fit
            the needs.

            .. note:: the mechanism is not perfect, security wise, but sparks
                is not oriented towards strict security in its current
                incarnation. Abusing it would be non-sense anyway, because
                people using it already have sysadmin rights on remote machines
                on which sparks will run.

            .. note:: for ``remote_configuration`` to be passed; you need to
                pass it as an argument to the ServiceRunner constructor.
                See the celery handling part for an example.

            .. versionadded:: 2.6
        """

        # In all cases, these context variables must exist and be empty,
        # to avoid letting some unresolved `%(var)s` in templates.
        context.update({
            'command_pre_args': '',
            'command_post_args': '',
        })

        custom_handler = getattr(self, 'custom_context_handler', None)

        if custom_handler is None:
            return

        remote_configuration = getattr(self, 'remote_configuration', None)

        temp_context = custom_handler(context.copy(), has_djsettings,
                                      remote_configuration)

        context['command_pre_args']  = temp_context['command_pre_args']
        context['command_post_args'] = temp_context['command_post_args']

    def restart_or_reload(self):
        """

            .. versionchanged:: in 3.0, support :program:`upstart`.
        """
       # cf. http://stackoverflow.com/a/9310434/654755

        if self.update:
            self.reload()

            if self.restart:
                self.stop(warn_only=True)
                self.start()
        else:
            # In any case, we restart the process during a {fast}deploy,
            # to reload the Django code even if configuration hasn't changed.

            self.stop()
            self.start()

    def find_configuration_or_template(self, service_name=None):
        """ Return a tuple of candidate configuration files or templates
            for the given :param:`service_name`, which defaults
            to ``supervisor`` if not supplied.
        """

        if service_name is None:
            service_name = self.service_handler

        role_name = get_current_role()

        candidates = (
            os.path.join(platform.django_settings.BASE_ROOT,
                         'config', service_name,
                         '{0}.conf'.format(self.program_name)),

            os.path.join(platform.django_settings.BASE_ROOT,
                         'config', service_name,
                         '{0}.template'.format(role_name)),

            os.path.join(platform.django_settings.BASE_ROOT,
                         'config', service_name,
                         '{0}.conf'.format(role_name)),

            # Last resort: the sparks template
            os.path.join(os.path.dirname(__file__),
                         'templates', service_name,
                         '{0}.template'.format(role_name))
        )

        # Last resort #2: if role is a worker, we have a meta-template.
        if role_name in worker_roles:
            candidates += (os.path.join(os.path.dirname(__file__),
                           'templates', service_name,
                           'worker.template'), )

        superconf = None

        # os.path.exists(): we are looking for a LOCAL file,
        # in the current Django project. Devops can prepare a
        # fully custom supervisor configuration file for the
        # Django web worker.
        for candidate in candidates:
            if os.path.exists(candidate):
                superconf = candidate
                break

        if superconf is None:
            raise RuntimeError('Could not find any configuration or '
                               'template for {0}. Searched {1}.'.format(
                                   self.program_name, candidates))

        return superconf

    def reload(self, check_installed=True):
        """ Reload the service manager configuration. """

        if not check_installed or (check_installed and self.installed):
            if self.service_handler == 'upstart':
                sudo("initctl reload {0} "
                     "|| initctl reload-configuration".format(
                         self.program_name), quiet=QUIET)
            else:
                sudo("supervisorctl update", quiet=QUIET)
        else:
            LOGGER.warning('Service configuration file {0} not '
                           'installed on {1}.'.format(self.program_name,
                                                      env.host_string))

    def stop(self, warn_only=True, check_installed=True):
        if not check_installed or (check_installed and self.installed):
            if self.service_handler == 'upstart':
                res = sudo("status {0} | grep 'stop/waiting' "
                           "|| stop {0}".format(self.program_name),
                           warn_only=warn_only, quiet=QUIET)
                if res.failed and res != 'stop: Unknown instance:' \
                        and not warn_only:
                    raise RuntimeError('Job failed to stop!')

            else:
                sudo("supervisorctl stop {0}".format(self.program_name),
                     warn_only=warn_only, quiet=QUIET)
        else:
            LOGGER.warning('Service configuration file {0} not '
                           'installed.'.format(self.program_name))

    def start(self):
        if self.installed:
            if self.service_handler == 'upstart':
                sudo("start {0}".format(self.program_name), quiet=QUIET)

            else:
                sudo("supervisorctl start {0}".format(self.program_name),
                     quiet=QUIET)
        else:
            LOGGER.warning('Service configuration file {0} not '
                           'installed.'.format(self.program_name))

    @property
    def installed(self):

        try:
            return self.__service_configuration_installed

        except:
            if self.service_handler == 'upstart':
                filename = '/etc/init/{0}.conf'.format(self.program_name)
            else:
                filename = '/etc/supervisor/conf.d/{0}.conf'.format(
                    self.program_name)

            self.__service_configuration_installed = exists(filename)

            return self.__service_configuration_installed

    def status(self):
        if self.installed:
            if self.service_handler == 'upstart':
                sudo('status {0}'.format(self.program_name), quiet=QUIET)

            else:
                sudo('supervisorctl status {0}'.format(self.program_name),
                     quiet=QUIET)
        else:
            LOGGER.warning('Service configuration file {0} not '
                           'installed.'.format(self.program_name))

    def remove(self):
        """ Stop the service, remove the configuration file, and reload the
            services manager (either :program:`upstart`
            or :program:`supervisor`).
        """

        if self.installed:
            self.stop(warn_only=True)

            if self.service_handler == 'upstart':
                sudo("rm /etc/init/{0}.conf".format(self.program_name), quiet=QUIET)

            else:
                sudo("rm /etc/supervisor/conf.d/{0}.conf".format(
                     self.program_name), quiet=QUIET)
            # NO need for self.reload(check_installed=False),
            # the property has still the cached value.
            self.reload()

            # Now every next call will notice the file doesn't exist.
            # There is no chance of desynchronization between real-life
            # file status and the cached property because the current
            # object is re-instanciated at every call.
            self.__service_configuration_installed = False
        else:
            LOGGER.warning('Service configuration file {0} not '
                           'installed.'.format(self.program_name))

    def configure_service(self, remote_configuration):
        """ Upload an environment-specific :program:`upstart`
            or :program:`supervisor` configuration file (depending on
            the ``remote_configuration`` parameter). The file is
            re-generated at each call in case configuration changed in
            the source repository.

            Upstart/Supervisor will be automatically restarted if
            configuration changed.

            Given ``root = remote_configuration.django_settings.BASE_ROOT``,
            this method will look for all these candidates (in order,
            first-match wins) for a given service:

                ${root}/config/${service}/${program_name}.conf
                ${root}/config/${service}/${role}.template
                ${root}/config/${service}/${role}.conf
                ${sparks_data_dir}/${service}/${role}.template

            The service template can end with either ``.conf`` or ``.template``.
            This is just for convenience: ``.template`` is more meaningful,
            but ``.conf`` is for consistency in the source repository. Whatever
            the name and suffix, all files will be treated the same (eg.
            rendered via Fabric's :func:`upload_template`).

            Templates are feeded with this context:

                context = {
                    'env': env.environment,
                    'root': env.root,
                    'user': env.user,
                    'role': <current-role-name>, (sparks specific)
                    'nice': <unix nice command> (default: ''),
                    'ionice': <unix ionice command> (default: ''),
                    'branch': env.branch,
                    'project': env.project,
                    'program': self.program_name,
                    'hostname': env.host_string,
                    'user_home': env.user_home
                        if hasattr(env, 'user_home')
                        else remote_configuration.tilde,
                    'virtualenv': env.virtualenv,
                    'worker_name': <the-friendly-worker-name> or '',
                    'worker_queues': <celery-queues-name> or '',
                }

            Regarding :program:`nice` and :program:`ionice` defaults, `sparks`
            Sets upsome of them:

                nice_defaults = {
                    'shell': '-n -7',
                    'flower': '-n 10',
                    'web': '-n -5',
                }

                ionice_defaults = {
                    'shell': '-c 2 -n 2',
                    'flower': '-c 3',
                }

            If you want NO defaults at all, just export the environment
            variables ``SPARKS_NICE_NODEFAULTS``
            and ``SPARKS_IONICE_NODEFAULTS`` to any value, and the defaults
            will not be used.

            .. note:: ``worker_name`` and ``worker_queues`` are filled by
                sparks and are internal values. If the current role is not
                worker related, the 2 fields will be ``''`` (empty string).

            Some **environment variables** can be added too
            (see :class:`add_environment_to_context` for details).

            In some specific cases, two other keys are added to context:

            - ``command_pre_args``
            - ``command_post_args``

            These two keys are just strings that will be prepended and suffixed
            to the final supervisor ``command`` directive.

            .. note:: this method assumes the remote machine is an
                Ubuntu/Debian server (physical or not), and will deploy
                supervisor configuration files
                to :file:`/etc/supervisor/conf.d/`.

            .. versionchanged:: Added :program:`upstart` support in version
                3.1. Prior to version 3.x, this method was named
                after ``configure_program``.

            .. versionchanged:: in version 2.6, the ``command_{pre,post}_args``
                were added, notably to handle installing more than one celery
                worker on the same machine.

        """

        superconf = self.find_configuration_or_template()

        # XXX/TODO: rename templates in sparks, create worker template.

        destination = '/etc/{0}/{1}.conf'.format(
            'init' if self.service_handler == 'upstart'
            else 'supervisor/conf.d', self.program_name)

        role_name = get_current_role()
        worker_name, worker_queues = worker_information_from_role(role_name)

        sparks_options = getattr(env, 'sparks_options', {})
        worker_queues_options = sparks_options.get('worker_queues', {})

        custom_queues = worker_queues_options.get(
            '%s@%s' % (role_name, env.host_string),
            worker_queues_options.get(
                '%s@%s' % (role_name[7:] or 'worker', env.host_string),
                worker_queues_options.get(
                    env.host_string,
                    worker_queues_options.get(role_name, None))))

        if custom_queues:
            worker_queues = custom_queues

        # NOTE: update docstring if you change this.
        context = {
            'env': env.environment,
            'root': env.root,
            'role': role_name,
            'user': env.user,
            'branch': env.branch,
            'project': env.project,
            'program': self.program_name,
            'hostname': env.host_string,
            #
            # MEGA HEADS UP: update this when we switch to Python 3…
            #
            'set_python_encoding': ('''echo "import sys; sys.setdefaultencoding('{0}')" ''' # NOQA
                                    ''' > {1}/.virtualenvs/{2}/lib/python2.7/sitecustomize.py''').format( # NOQA
                                    env.encoding,
                                    env.user_home
                                       if hasattr(env, 'user_home')
                                       else remote_configuration.tilde,
                                    env.virtualenv)
                if hasattr(env, 'encoding') else '',
            'user_home': env.user_home
                if hasattr(env, 'user_home')
                else remote_configuration.tilde,
            'virtualenv': env.virtualenv,
            'worker_name': worker_name,
            'worker_queues': worker_queues,
        }

        for nice, sparks_defaults, nice_env_variable in (
            ('nice', ServiceRunner.nice_defaults, 'SPARKS_NICE_NODEFAULTS'),
            ('ionice', ServiceRunner.ionice_defaults,
             'SPARKS_IONICE_NODEFAULTS')):

            niceargs = sparks_options.get(nice + '_arguments', {})

            if os.environ.get(nice_env_variable, False):
                LOGGER.warning(u'Not using sparks defaults for %s command '
                               u'because %s variable is set.',
                               nice, nice_env_variable)
                defaults = {}
            else:
                defaults = sparks_defaults

            #LOGGER.debug(niceargs)

            my_niceargs = niceargs.get(
                '%s@%s' % (role_name, env.host_string),
                niceargs.get(
                    '%s@%s' % (role_name[7:] or 'worker', env.host_string),
                    niceargs.get(
                        env.host_string,
                        niceargs.get(role_name,
                                     defaults.get(role_name,
                                                  defaults.get('__all__',
                                                               None))))))
            #LOGGER.debug(my_niceargs)

            if my_niceargs:
                context[nice] = '%s %s' % (nice, my_niceargs)

            else:
                # Set an empty value to be sure the
                # variable name is replaced in the template.
                context[nice] = ''

        #LOGGER.debug(context)

        self.add_environment_to_context(context, self.has_djsettings)
        self.add_command_pre_post_to_context(context, self.has_djsettings)

        if exists(destination):
            upload_template(superconf, destination + '.new',
                            context=context, use_sudo=True, backup=False)

            if sudo('diff {0} {0}.new'.format(destination),
                    warn_only=True, quiet=QUIET) == '':
                sudo('rm -f {0}.new'.format(destination), quiet=QUIET)

            else:
                self.stop()
                sudo('mv {0}.new {0}'.format(destination), quiet=QUIET)
                self.update  = True
                self.restart = True

        else:
            upload_template(superconf, destination, context=context,
                            use_sudo=True, backup=False)
            # No need to restart, the update will
            # add the new program and start it
            # automatically, thanks to supervisor.
            self.update = True

            # We installed the file, be sure to update the cached property.
            # There is no chance of desynchronization between real-life
            # file status and the cached property because the current
            # object is re-instanciated at every call.
            self.__service_configuration_installed = True

    def handle_gunicorn_config(self):
        """ Upload a gunicorn configuration file to the server. Principle
            is exactly the same as the supervisor configuration. Looked
            up paths are the similar, except that the method will look
            for them in the :file:`gunicorn/` subdir instead
            of :file:`supervisor/`.
        """

        guniconf = self.find_configuration_or_template('gunicorn')
        gunidest = os.path.join(env.root, 'config', 'gunicorn',
                                '{0}.conf'.format(self.program_name))

        # NOTE: as the configuration file stays in config/ — which is
        # is a git managed directory – and is not templated at all, we
        # are double-checking a file that is already good, most of the time.
        #
        # BUT, in case of a migration, where the developers just created
        # a new config file whereas before there wasn't any, this will
        # make the migration process appear natural; the user won't be
        # annoyed with a 'please move <file> out of the way' GIT message,
        # and won't be required to make a manual operation.

        if exists(gunidest):
            put(guniconf, gunidest + '.new')

            if sudo('diff {0} {0}.new'.format(gunidest),
                    warn_only=True, quiet=QUIET) == '':
                sudo('rm -f {0}.new'.format(gunidest), quiet=QUIET)

            else:
                sudo('mv {0}.new {0}'.format(gunidest), quiet=QUIET)
                self.update  = True
                self.restart = True

        else:
            gunidestdir = os.path.dirname(gunidest)

            if not exists(gunidestdir):
                run('mkdir -p "{0}"'.format(gunidestdir), quiet=QUIET)

            # copy the default configuration to remote.
            put(guniconf, gunidest)

            if not self.update:
                self.restart = True


# ••••••••••••••••••••••••••••••••••••••••••••••••••••• commands & global tasks


@task(aliases=('command', 'cmd'))
def run_command(cmd):
    """ Run a command on the remote side.

    The command will be run inside the virtualenv and ch'ed
    into ``env.root``. Use like this (but don't do this in production):

    fab test cmd:'./manage.py reset admin --noinput'

    .. versionadded:: in 2.0.
    """

    # Wrap the real task to eventually run on all hosts it none specified.
    execute_or_not(run_command_task, cmd)


@task
def sed_command_task(*args, **kwargs):
    """ Fabric task for a :prog:`sed` command. """

    with activate_venv():
        with cd(env.root):
            sed(*args, **kwargs)


@task(aliases=('sed', ))
def sed_command(*args, **kwargs):
    """ Run a :prog:`sed` command on the remote side.

    Inside the virtualenv
    and ch'ed into ``env.root``. Use like this (but don't do this in
    production)::

        # In fact, this WON'T work because of spaces and equals signs.
        #   fab test sed:.git/config,'url = olive@','url = git@'
        # You should try avoiding them, and this should work:
        fab test sdf.sed:.git/config,'(url.*)olive@','\1git@'

    Reminder of Fabric 1.6.1 ``sed`` function arguments::

        filename, before, after, limit='', use_sudo=False,
        backup='.bak', flags='', shell=False

    .. versionadded:: in 2.8.
    """

    # Wrap the real task to eventually run on all hosts it none specified.
    execute_or_not(sed_command_task, *args, **kwargs)


@task
def run_command_task(cmd):

    with activate_venv():
        with cd(env.root):
            run(cmd, quiet=QUIET)


@task(aliases=('base', 'base_components'))
@with_remote_configuration
def install_components(remote_configuration=None, upgrade=False):
    """ Install necessary packages to run a full Django stack.

        .. todo:: terminate this task. It is not usable yet, except on
            an OSX development-only machine. Others (servers, test &
            production) are not implemented yet and require manual
            installation / configuration.

            - split me into packages/modules where appropriate.
            - split me into server and clients packages.

        .. note:: server configuration / deployment can nevertheless be
            leveraged by:

            - a part of ``sparks.fabfile.*`` which contains server tasks,
            - and by the fact that many Django services are managed by
              the project requirements (thus installed automatically) and
              via supervisord. Thus, on the worker/web side, only
              supervisord requires to be installed. On other machines,
              redis/memcached/PostgreSQL/MongoDB and friends remain to
              be loved by your sysadmin skills.
    """

    LOGGER.info('Checking installed components…')

    with cd(env.root):
        fabfile.dev()
        fabfile.dev_web_nodejs()
        fabfile.dev_web_ruby()
        #fabfile.dev_web_pyside()
        fabfile.dev_django_full()

    # OSX == test environment == no nginx/supervisor/etc
    if remote_configuration.is_osx:

        LOGGER.warning('Considering a development environment, '
                       'installing everything on OSX.')

        pkg.pkg_add(('nginx', ))

        # If you want to host pages on your local machine to the wider network
        # you can change the port to 80 in: /usr/local/etc/nginx/nginx.conf
        # You will then need to run nginx as root: `sudo nginx`.

        run('ln -sfv /usr/local/opt/nginx/*.plist ~/Library/LaunchAgents',
            quiet=QUIET)
        run('launchctl load ~/Library/LaunchAgents/homebrew.mxcl.nginx.plist',
            quiet=QUIET)

        fabfile.db_redis()
        fabfile.db_postgresql()
        fabfile.db_mongodb()
        fabfile.db_memcached()

        # 'rabbitmq'
        # run('ln -sfv /usr/local/opt/rabbitmq/*.plist ~/Library/LaunchAgents',
        #     quiet=QUIET)
        # run('launchctl load ~/Library/LaunchAgents/homebrew.*.rabbitmq.plist',
        #     quiet=QUIET)

    else:
        current_role = get_current_role()

        if current_role == 'web':
            pkg.pkg_add(('nginx-full' if remote_configuration.is_deb
                        else 'nginx' if remote_configuration.is_arch
                        else ('www/apache24'
                        if env.web_use_apache else 'www/nginx'), ))

        if is_local_environment():
            LOGGER.info('Installing all services for a local development '
                        'environment…')

            # These are duplicated here in case env.host_string has been
            # manually set to localhost in fabfile, which I do myself.
            pkg.pkg_add(('nginx-full' if remote_configuration.is_deb
                        else 'nginx' if remote_configuration.is_arch
                        else 'www/nginx', ))

            fabfile.db_redis()
            fabfile.db_memcached()
            fabfile.db_postgresql()
            fabfile.db_mongodb()

        else:
            LOGGER.warning('NOT installing redis/PostgreSQL/MongoDB/Memcache '
                           'on anything other than local developement envs.')

# ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Helpers


def get_git_branch():
    """ Return either ``env.branch`` if defined, else ``master`` if environment
        is ``production``, or ``develop`` if anything else than ``production``
        (we use the :program:`git-flow` branching model). """

    branch = env.branch

    if branch == '<GIT-FLOW-DEPENDANT>':
        branch = 'master' if 'production' in env.environment else 'develop'

    return branch


class activate_venv(object):
    """ Activate the virtualenv at the Fabric level.

        Additionnaly, try to deal gently with virtualenvwrapper's
        :file:`.project` file, which totally borks the remote path
        and anihilates Fabric's ``cd()`` benefits in normal conditions.

        For performance reasons, remote calls are done only at first call.
        If for some reason you would like to refresh the class values, you
        should file a pull request and implement the needed work
        in the :meth:`__call__` method.

        .. versionadded:: 2.5.
    """

    # Keep them as class objects, they never change…
    project_file = None
    has_project  = None
    use_jenkins  = None

    def __init__(self):

        if activate_venv.has_project is None:

            activate_venv.use_jenkins = bool(os.environ.get(
                                             'SPARKS_JENKINS', False))

            if not activate_venv.use_jenkins:

                workon_home = run('echo $WORKON_HOME', quiet=QUIET).strip() \
                    or '${HOME}/.virtualenvs'

                activate_venv.project_file = os.path.join(workon_home,
                                                          env.virtualenv,
                                                          '.project')
                activate_venv.has_project  = exists(activate_venv.project_file)

        self.my_prefix = prefix(
            'source {0}/venv/bin/activate'.format(env.root)) \
            if activate_venv.use_jenkins \
            else prefix('workon %s' % env.virtualenv)

    def __call__(self, *args, **kwargs):
        return self

    def __enter__(self):
        if activate_venv.has_project:
            run('mv "{0}" "{0}.disabled"'.format(activate_venv.project_file),
                quiet=QUIET)

        self.my_prefix.__enter__()

    def __exit__(self, *args, **kwargs):

        self.my_prefix.__exit__(*args, **kwargs)

        if activate_venv.has_project:
            run('mv "{0}.disabled" "{0}"'.format(activate_venv.project_file),
                quiet=QUIET)


def sparks_djsettings_env_var():

    # The trailing space is intentional. Callers expect us to have inserted
    # it if we setup the shell environment variable.
    return 'SPARKS_DJANGO_SETTINGS={0} '.format(
        env.sparks_djsettings) if hasattr(env, 'sparks_djsettings') else ''


def django_settings_env_var():

    # The trailing space is intentional. Callers expect us to have inserted
    # it if we setup the shell environment variable.
    return 'DJANGO_SETTINGS_MODULE={0}.settings '.format(
        env.project) if hasattr(env, 'project') else ''


def get_all_fixtures(order_by=None):
    """ Find all fixtures files in the current project, eg. files whose name
        ends with ``.json`` and which are located in any `fixtures/` directory.

        :param order_by: a string. Currently only ``'date'`` is supported.

        .. note:: the action takes place on the current machine, eg. it uses
            ``Fabric's`` :func:`local` function.

        .. versionadded:: 1.16
    """

    # OMG: http://stackoverflow.com/a/11456468/654755 ILOVESO!

    if order_by is None:
        return local("find . -name '*.json' -path '*/fixtures/*'",
                     capture=True).splitlines()

    elif order_by == 'date':
        return local("find . -name '*.json' -path '*/fixtures/*' -print0 "
                     "| xargs -0 ls -1t", capture=True).splitlines()

    else:
        raise RuntimeError('Bad order_by value "{0}"'.format(order_by))


def new_fixture_filename(app_model):
    """

        .. versionadded:: 1.16
    """

    def fixture_name(base, counter):
        return '{0}_{1:04d}.json'.format(base, counter)

    try:
        app, model = app_model.split('.', 1)

    except ValueError:
        app   = app_model
        model = None

    fixtures_dir = os.path.join(env.project, app, 'fixtures')

    if not os.path.exists(fixtures_dir):
        os.makedirs(fixtures_dir)

    # WARNING: no dot '.' in fixtures names, else Django fails to install it.
    # 20130514: CommandError: Problem installing fixture 'landing':
    # 2013-05-14_0001 is not a known serialization format.
    new_fixture_base = os.path.join(fixtures_dir, '{0}{1}_{2}'.format(app,
                                    '' if model is None else ('.' + model),
                                    datetime.date.today().isoformat()))

    fix_counter = 1
    new_fixture_name = fixture_name(new_fixture_base, fix_counter)

    while os.path.exists(new_fixture_name):
        fix_counter += 1
        new_fixture_name = fixture_name(new_fixture_base, fix_counter)

    return new_fixture_name

# •••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Code related


@task
def init_environment():
    """ Create ``env.root`` on the remote side, and the ``env.virtualenv``
        it they do not exist.

        if ``env.repository`` exists, the following command will be run
        automatically::

            git clone ${env.repository} ${env.root}

        Else, the user will be prompted to create the repository manually
        before continuing.

    """

    LOGGER.info('Creating environment…')

    if not exists(env.root):
        run('mkdir -p "{0}"'.format(os.path.dirname(env.root)), quiet=QUIET)

        if hasattr(env, 'repository'):
            repositories  = env.get('sparks_options', {}).get('repository', {})
            my_repository = repositories.get(env.host_string, env.repository)

            run("git clone {0} {1}".format(my_repository, env.root),
                quiet=QUIET)

        else:
            prompt(u'Please create the git repository in {0}:{1} and press '
                   u'[enter] when done.\nIf you want it to be cloned '
                   u'automatically, just define `env.repository` in '
                   u'your fabfile.'.format(env.host_string, env.root))

    if run('lsvirtualenv | grep {0}'.format(env.virtualenv),
           warn_only=True, quiet=QUIET).strip() == '':
        run('mkvirtualenv {0}'.format(env.virtualenv), quiet=QUIET)


@task
def pre_requirements_task(fast=False, upgrade=False):

    if is_local_environment():
        return

    role_name = get_current_role()

    custom_script = os.path.join(env.root, env.requirements_dir,
                                 role_name + '.sh')

    has_custom_script = exists(custom_script)

    if not has_custom_script:
        return

    LOGGER.info('Running custom requirements script (preinstall)…')

    with cd(env.root):
        with activate_venv():
            run('bash "{0}" preinstall "{1}" "{2}" "{3}" "{4}"'.format(
                custom_script, env.environment, env.virtualenv,
                role_name, env.host_string), quiet=QUIET)


@task
def post_requirements_task(fast=False, upgrade=False):

    #
    # TODO: factorize role_name and exists() with pre_requirements_task
    #

    if is_local_environment():
        return

    role_name = get_current_role()

    custom_script = os.path.join(env.root, env.requirements_dir,
                                 role_name + '.sh')

    has_custom_script = exists(custom_script)

    if not has_custom_script:
        return

    LOGGER.info('Running custom requirements script (install)…')

    with cd(env.root):
        with activate_venv():
            run('bash "{0}" install "{1}" "{2}" "{3}" "{4}"'.format(
                custom_script, env.environment, env.virtualenv,
                role_name, env.host_string), quiet=QUIET)


def requirements_task(fast=False, upgrade=False):

    # Thanks http://stackoverflow.com/a/9362082/654755
    if upgrade:
        command = 'yes w | {sparks_env}{django_env} pip install -U'
    else:
        command = 'yes w | {sparks_env}{django_env} pip install'

    command = command.format(sparks_env=sparks_djsettings_env_var(),
                             django_env=django_settings_env_var())

    with cd(env.root):

        pip_cache = os.path.join(env.root, '.pipcache')

        if not exists(pip_cache):
            run('mkdir -p {0}'.format(pip_cache), quiet=QUIET)

        with activate_venv():

            if is_development_environment():

                LOGGER.info('Checking development requirements…')

                dev_req = os.path.join(env.root, env.dev_requirements_file)

                if exists(dev_req):
                    run(u"{command} --download-cache {pip_cache} "
                        u"--requirement {requirements_file}".format(
                        command=command, requirements_file=dev_req,
                        pip_cache=pip_cache), quiet=QUIET)

            LOGGER.info('Checking requirements…')

            req = os.path.join(env.root, env.requirements_file)

            if exists(req):
                run(u"{command} --download-cache {pip_cache} "
                    u" --requirement {requirements_file}".format(
                    command=command, requirements_file=req,
                    pip_cache=pip_cache), quiet=QUIET)

            # ——————————————————————————————————————————————————————— Ruby gems

            req = os.path.join(env.root, env.gem_file)

            if exists(req):
                run(u"bundle install --gemfile={gemfile}".format(
                    gemfile=req), quiet=QUIET)

            LOGGER.info('Done checking requirements.')


@task(alias='req')
def requirements(fast=False, upgrade=False):
    """ Install PIP requirements (and dev-requirements).

        .. note:: :param:`fast` is not used yet, but exists for consistency
            with other fab tasks which handle it.
    """

    roles_to_run = set(all_roles)

    for req_task in (pre_requirements_task,
                     requirements_task,
                     post_requirements_task):

        execute_or_not(req_task,
                       fast=fast, upgrade=upgrade,
                       sparks_roles=roles_to_run)


def push_environment_task(project_envs_dir, fast=False, force=False):
    """ Push environment file (Fabric task). """

    role_name = get_current_role()

    not_found = True

    for env_file_candidate in (
        '{0}.env'.format(env.host_string.lower()),
        '{0}_{0}.env'.format(role_name, env.environment),
        '{0}.env'.format(env.environment),
            'default.env', ):
        candidate_fullpath = os.path.join(project_envs_dir, env_file_candidate)

        if os.path.exists(candidate_fullpath):
            put(candidate_fullpath, '.env')
            not_found = False
            break

    if not_found:
        raise RuntimeError(u'$SPARKS_ENV_DIR is defined but no environment '
                           u'file matched {0} in {1}!'.format(env.host_string,
                                                              project_envs_dir))

    # Push a global SSH key too, to be able to execute remote
    # tasks (eg. from cron jobs) from any machine to any other.
    #env_ssh_path = os.path.join(project_envs_dir, 'ssh/id_dsa')

    # if os.path.exists(env_ssh_path):
    #     if force or not exists('.ssh/id_dsa'):
    #         put(env_ssh_path, '.ssh/id_dsa')
    #         put(env_ssh_path + '.pub', '.ssh/id_dsa.pub')

    # XXX: append SSH key only if not already appended.


@task(task_class=DjangoTask, aliases=('env', 'environment', ))
def push_environment(fast=False, force=False):
    """ Copy any environment file to the remote server in ``~/.env``,
        ready to be loaded by the shell when the user does anything.

        Environment files are shell scripts, they should be loaded
        via ``. ~/.env`` on the remote host.

        Master environment dir is indicated to :program:`sparks` via
        the environment variable ``SPARKS_ENV_DIR``. In this directory,
        sparks will look for a subdirectory named after
        Fabric's ``env.project``.

        In the project directory, *sparks* will lookup, in this order of
        preferences:

        - ``<remote_hostname_in_lowercase>.env`` (eg. ``1flow.io.env``)
        - ``<remote_host_role>_<env.environment>.env``
          (eg. ``web_production.env``)
        - ``<env.environment>.env`` (eg. ``production.env``)
        - ``default.env`` (in case you have only one environment file)

        The first that matches is the one that will be pushed.

        There is no kind of inclusion nor concatenation mechanism for now.

        .. versionadded:: 3.0

    """

    envs_dir = os.environ.get('SPARKS_ENV_DIR', None)

    if envs_dir is None:
        LOGGER.warning('$SPARKS_ENV_DIR is not defined, will not push any '
                       'environment file to any remote host.')
        return

    if u'~' in envs_dir:
        envs_dir = os.path.expanduser(envs_dir)

    if u'$' in envs_dir:
        envs_dir = os.path.expandvars(envs_dir)

    project_envs_dir = os.path.join(envs_dir, env.project)

    if not os.path.exists(project_envs_dir):
        LOGGER.warning('$SPARKS_ENV_DIR/{0} does not exist. Will not push any '
                       'environment file to any remote host.'.format(
                           env.project))
        return

    LOGGER.info('Pushing environment files…')

    # re-wrap the internal task via execute() to catch roledefs.
    execute_or_not(push_environment_task, project_envs_dir, fast=fast,
                   force=force, sparks_roles=all_roles)


@task(alias='update_task')
def git_update_task():
    """ Push latest code from local to origin, checkout branch on remote. """

    with cd(env.root):
        if not is_local_environment():
            run('git checkout %s' % get_git_branch(), quiet=QUIET)


@task(task_class=DjangoTask, aliases=('update', 'checkout', ))
def git_update():
    """ Sparks wrapper task for :func:`git_update_task`. """

    execute_or_not(git_update_task,
                   sparks_roles=['web']
                   + worker_roles[:]
                   + ['beat', 'flower', 'shell'])


@serial
@task(alias='pull_task')
def git_pull_task():
    """ Pull latest code from origin to remote,
        reload sparks settings if changes.

        Serial task to avoid git lock conflicts on central repository.
    """

    with cd(env.root):
        run('git pull', quiet=QUIET)


@task(task_class=DjangoTask, aliases=('pull', ))
def git_pull(filename=None, confirm=True):
    """ Sparks wrapper task for :func:`git_pull_task`. """

    # re-wrap the internal task via execute() to catch roledefs.
    # TODO: roles should be "__any__".except('db')
    execute_or_not(git_pull_task, sparks_roles=['web'] + worker_roles[:]
                   + ['beat', 'flower', 'shell'])


@task(alias='clean_task')
def git_clean_task():
    """ clean old Python compiled files. To avoid crashes like this one:

        http://dev.1flow.net/webapps/obi1flow/group/783/

        Which occured after removing profiles/admin.py and emptying models.py
        but admin.pyc was left il place and refered to an ancient model…
    """

    with cd(env.root):
        run("find . \( -name '*.pyc' -or -name '*.pyo' \) -print0 "
            " | xargs -0 rm -f", warn_only=True, quiet=QUIET)


@task(task_class=DjangoTask, aliases=('clean', ))
def git_clean():
    """ Sparks wrapper task for :func:`git_clean_task`. """

    # re-wrap the internal task via execute() to catch roledefs.
    # TODO: roles should be "__any__".except('db')
    execute_or_not(git_clean_task, sparks_roles=['web'] + worker_roles[:]
                   + ['beat', 'flower', 'shell'])


@task(alias='getlangs')
@with_remote_configuration
def push_translations(remote_configuration=None):
    """ If new gettext translations are available on remote, commit and push them. """ # NOQA

    try:
        if not remote_configuration.django_settings.DEBUG:
            # remote translations are fetched only on development / test
            # environments. Production are not meant to host i18n work.
            return

    except AttributeError:
        LOGGER.warning('push_translations() ignored, remote Django settings '
                       'cannot be loaded (you can ignore this warning during '
                       'first deployment.')
        return

    LOGGER.info('Checking for new translations…')

    with cd(env.root):
        if run("git status | grep -E 'modified:.*locale.*django.po' "
               "|| true", quiet=QUIET) != '':
            run(('git add -u \*locale\*po '
                '&& git commit -m "{0}" '
                 # If there are pending commits in the central, `git push` will
                 # fail if we don't pull them prior to pushing local changes.
                 '&& (git up || git pull) && git push').format(
                     'Automated l10n translations from {0} on {1}.').format(
                         env.host_string, datetime.datetime.now().isoformat()),
                quiet=QUIET)

            # Get the translations changes back locally.
            # Don't fail if the local user doesn't have git-up,
            # and try to pull the standard way.
            local('git up || git pull', capture=QUIET)


# •••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Services


@task(alias='nginx')
def service_action_nginx(fast=False, action=None):
    """ Restart the remote nginx (if installed),
        after having refreshed its configuration file. """

    if action is None:
        action = 'status'

    if not exists('/etc/nginx'):
        return

    # Nothing implemented yet.
    return

    # if action == 'restart':
    #     service_runner.stop()
    #     service_runner.start()

    # else:
    #     getattr(service_runner, action)()


@task(task_class=DjangoTask, alias='gunicorn')
@with_remote_configuration
def service_action_webserver_gunicorn(remote_configuration=None, fast=False,
                                      action=None):
    """ (Re-)upload configuration files and reload gunicorn via supervisor.

        This will reload only one service, even if supervisor handles more
        than one on the remote server. Thus it's safe for production to
        reload test :-)

    """

    if action is None:
        action = 'status'

    has_djsettings, program_name = ServiceRunner.build_program_name()

    service_runner = ServiceRunner(from_dict={
                                   'has_djsettings': has_djsettings,
                                   'program_name': program_name
                                   })

    if action != "stop" and not fast:
        service_runner.configure_service(remote_configuration)
        service_runner.handle_gunicorn_config()

    if action == 'restart':
        service_runner.stop()
        service_runner.start()

    else:
        getattr(service_runner, action)()


def worker_options(context, has_djsettings, remote_configuration):
    """ This is the celery custom context handler. It will add
        the ``--hostname`` argument to the celery command line, as suggested
        at http://docs.celeryproject.org/
            en/latest/userguide/workers.html#starting-the-worker
        Inconditionnaly, to allow live manipulations of workers in
        running clusters.
    """

    def get_option(from_dict, role_name, use__all__=True):
        return from_dict.get(

            # Try "queue_full_name@hostname"
            '%s@%s' % (role_name, env.host_string),
            from_dict.get(

                # Then "queue@hostname"
                '%s@%s' % (role_name[7:] or 'worker', env.host_string),
                from_dict.get(

                    # Then, "hostname"
                    env.host_string,
                    from_dict.get(

                        # Then "queue"
                        role_name,

                        # And finally "__all__" for a global default.
                        from_dict.get('__all__', None)
                        if use__all__ else None
                    )
                )
            )
        )

    command_pre_args  = ''
    command_post_args = ''

    role_name = get_current_role()

    if role_name in worker_roles:
        try:
            short_hostname, domain_name = env.host_string.split('.', 1)
        except:
            short_hostname, domain_name = env.host_string, 'local'

        command_post_args += '--hostname {0}-{1}.{2}'.format(
            # strip 'worker_', eg. display only 'net_medium' or
            # 'io_low'. Use a dash (and not a dot) so celery
            # displays [celeryd@hostname-queue…] in process lists.
            short_hostname, role_name[7:], domain_name)

        sparks_options = getattr(env, 'sparks_options', {})

        # TODO: '5' should be 'if remote_configuration.is_lxc'
        # but we don't have this configuration attribute yet.

        for dict_name, opt_string, use_all in (
            ('worker_pool',            ' -P {0}',                 True),
            ('worker_time_limit',      ' --time-limit {0}',       True),
            ('worker_soft_time_limit', ' --soft-time-limit {0}',  True),
            ('worker_concurrency',     ' -c {0}',                 True),
            ('autoscale',              ' --autoscale {0}',        True),
            ('max_tasks_per_child',    ' --maxtasksperchild={0}', True),
            ('custom_arguments',       ' {0}',                    True),
        ):

            opt_value = get_option(sparks_options.get(dict_name, {}),
                                   role_name, use__all__=use_all)

            if opt_value:
                command_post_args += opt_string.format(opt_value)

    elif role_name == 'flower':
        try:
            broker = remote_configuration.django_settings.BROKER_URL

        except:
            LOGGER.warning('Could not get BROKER_URL in remote Django settings')
            broker = ''

        if broker.startswith('redis://'):
            # As advised in https://github.com/mher/flower/issues/114#issuecomment-22213390 # NOQA
            # We patch the flower template to make the redis broker inspection
            # work "again" as expected (as much as possible, because many
            # columns are still empty, but at least we got the number of
            # messages, which is better than nothing).
            command_post_args += ' --broker={0} --broker_api={0}'.format(broker)

        elif broker.startswith('amqp://'):
            # And for AMQP: http://stackoverflow.com/a/25943620/654755

            broker_api = os.environ.get('BROKER_API', None)

            if broker_api is None:
                # Replace amqp:// by http:// ; replace vhost by /api.
                broker_api = 'http' + broker.rsplit('/', 1)[0][4:] + '/api'

                # Port is 55672 instead of 5672 (RabbitMQ 2.7
                # on Ubuntu 12.04 LTS), else it's 15672 on
                # ArchLinux (version 3.4…)
                broker_api = broker_api.replace(':5', ':55')

            command_post_args += ' --broker={0} --broker_api={1}'.format(
                broker, broker_api)

        else:
            LOGGER.warning(u'Unsupported broker, BROKER_API will be empty. '
                           u'Flower will probably not work correctly.')

    elif role_name == 'shell':
        sparks_options = getattr(env, 'sparks_options', {})
        shell_arguments = sparks_options.get('shell_arguments', {})

        command_pre_args += ' ' + shell_arguments.get('command_pre_args', '')
        command_post_args += ' ' + shell_arguments.get('command_post_args', '')

    context.update({
        'command_pre_args': command_pre_args,
        'command_post_args': command_post_args,
    })

    return context


@task(task_class=DjangoTask, alias='celery')
@with_remote_configuration
def service_action_worker_celery(remote_configuration=None, fast=False,
                                 action=None):
    """ (Re-)upload configuration files and reload celery via supervisor.

        This will reload only one service, even if supervisor handles more
        than one on the remote server. Thus it's safe for production to
        reload test :-)

    """

    if action is None:
        action = 'restart'

    has_djsettings, program_name = ServiceRunner.build_program_name()

    service_runner = ServiceRunner(from_dict={
                                   'has_djsettings': has_djsettings,
                                   'program_name': program_name,
                                   'custom_context_handler': worker_options,
                                   'remote_configuration':
                                   remote_configuration,
                                   })

    if action != "stop" and not fast:
        service_runner.configure_service(remote_configuration)
        # NO need:
        #   service_runner.handle_celery_config(<role>)

    if action == 'restart':
        service_runner.stop()
        service_runner.start()

    else:
        getattr(service_runner, action)()


# •••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Django tasks

@task(task_class=DjangoTask, alias='manage')
def django_manage(command, prefix=None, **kwargs):
    """ Calls a remote :program:`./manage.py`. Obviously, it will setup all
        the needed shell environment for the call to succeed.

        Not meant for complex calls (eg. makemessages in different directories
        than the project root). If you need more flexibility, call the command
        yourself, like ``sparks`` does in the :func:`handlemessages` function.

        :param command: the django manage command as a simple string,
            eg. ``'syncdb --noinput'``. Default: ``None``, but you must
            provide one, else manage will print its help (at best).

        :param prefix: a string that will be inserted at the start of the
            final command. For a badly implemented command which doesn't
            accept the ``--noinput`` argument, you can use ``prefix='yes | '``.
            Don't forget spaces if you want readability, the prefix will be
            inserted verbatim. Default: ``''``.

        :param kwargs: the remaining arguments are passed to
            fabric's :func:`run` method via the ``**kwargs`` mechanism.

        .. versionadded:: 1.16.

    """

    if prefix is None:
        prefix = ''

    with activate_venv():
        with cd(env.root):
            return run('{0}{1}./manage.py {2} --verbosity 1 --traceback'.format(
                       prefix, sparks_djsettings_env_var(), command),
                       quiet=QUIET, **kwargs)


@with_remote_configuration
def handlemessages(remote_configuration=None, mode=None):
    """ Run the Django compilemessages management command.

        set ``SPARKS_DONT_TRANSLATE_LANGUAGE_CODE`` in the project environment
        if you do not want the main language to show in translations. This is
        the case for example if i18n strings in your code are in english or
        your native language. Setting the variable to any value makes it
        detected as ``True``. **For default behaviour, unset it completely.**

        If you use codes like ``exception.object.display_message`` and not
        plain sentences (which is the case of 1flow since 20140505), even the
        main Django LANGUAGE_CODE will show up in translations.

        .. note:: not a Fabric task, but a helper function.
    """

    if mode is None:
        mode = 'make'

    elif mode not in ('make', 'compile'):
        raise RuntimeError(
            '"mode" argument must be either "make" or "compile".')

    show_english = not os.environ.get('SPARKS_DONT_TRANSLATE_LANGUAGE_CODE',
                                      False)

    def compile_internal(run_from):
        for language in languages:
            run('{0}{1}./manage.py {2}messages --locale {3}'.format(
                sparks_djsettings_env_var(), run_from, mode, language),
                quiet=QUIET)

    # Transform language codes (eg. 'fr-fr') to locale names (eg. 'fr_FR'),
    # keeping extensions (eg. '.utf-8'), but don't touch short codes (eg. 'en').
    languages = [('{0}_{1}{2}'.format(code[:2], code[3:5].upper(), code[5:])
                 if len(code) > 2 else code) for code, name
                 in remote_configuration.django_settings.LANGUAGES
                 if show_english
                 or code != remote_configuration.django_settings.LANGUAGE_CODE]

    project_apps = [app.split('.', 1)[1] for app
                    in remote_configuration.django_settings.INSTALLED_APPS
                    if app.startswith('{0}.'.format(env.project))]

    with activate_venv():
        with cd(env.root):
            with cd(env.project):
                if exists('locale'):
                    compile_internal(run_from='../')

                else:
                    for short_app_name in project_apps:
                        with cd(short_app_name):
                            LOGGER.info('Compiling language files for app %s…',
                                        short_app_name)
                            compile_internal(run_from='../../')


@task
def makemessages_task():
    """ Django compile messages dirty job. """

    handlemessages(mode='make')


@task(task_class=DjangoTask, alias='messages')
def makemessages():
    """ The sparks wrapper for make message fabric task. """

    execute_or_not(makemessages_task, sparks_roles=['web'] + worker_roles[:])
    # NO NEED: + ['beat', 'flower', 'shell'])


@task
def compilemessages_task():
    """ Django compile messages dirty job. """

    handlemessages(mode='compile')


@task(task_class=DjangoTask, alias='compile')
def compilemessages():
    """ The sparks wrapper for compile message fabric task. """

    execute_or_not(compilemessages_task, sparks_roles=['web'] + worker_roles[:])
    # NO NEED: + ['beat', 'flower', 'shell'])


@task(task_class=DjangoTask)
@with_remote_configuration
def createdb(remote_configuration=None, db=None, user=None, password=None,
             installation=False):
    """ Create the PostgreSQL user & database if they don't already exist.
        Install PostgreSQL on the remote system if asked to. """

    LOGGER.info('Checking database setup…')

    if installation:
        from ..fabric import fabfile
        fabfile.db_postgresql()

    db, user, password = pg.temper_db_args(db=db, user=user, password=password)

    if is_local_environment():
        pg_env = []

    else:
        SPARKS_PG_SUPERUSER = os.environ.get('SPARKS_PG_SUPERUSER', None)
        SPARKS_PG_SUPERPASS = os.environ.get('SPARKS_PG_SUPERPASS', None)
        SPARKS_PG_TMPL_DB   = os.environ.get('SPARKS_PG_TMPL_DB',   None)

        pg_env = ['PGUSER={0}'.format(SPARKS_PG_SUPERUSER)
                  if SPARKS_PG_SUPERUSER else '',
                  'PGPASSWORD={0}'.format(SPARKS_PG_SUPERPASS)
                  if SPARKS_PG_SUPERPASS else '']

        pg_env.append('PGDATABASE={0}'.format(SPARKS_PG_TMPL_DB or 'template1'))

    djsettings = getattr(remote_configuration, 'django_settings', None)

    if djsettings is not None:
        db_setting = djsettings.DATABASES['default']
        db_host    = db_setting.get('HOST', None)
        db_port    = db_setting.get('PORT', None)

        if db_host is not None and not is_localhost(db_host):
            pg_env.append('PGHOST={0}'.format(db_host))

        if db_port is not None and db_port != u'':
            pg_env.append('PGPORT={0}'.format(db_port))

    # flatten the list
    pg_env  = ' '.join(pg_env)
    pg_role = pg.get_admin_user()

    LOGGER.info(u'Using PosgreSQL role “%s” and environment “%s”.',
                pg_role, pg_env)

    with settings(sudo_user=pg_role):

        # WARNING: don't .strip() here, else we fail Fabric's attributes.
        db_user_result = pg.wrapped_sudo(pg.SELECT_USER.format(
            pg_env=pg_env, user=user), warn_only=True, quiet=QUIET)

        if db_user_result.strip() == '':
            create_user_result = pg.wrapped_sudo(pg.CREATE_USER.format(
                pg_env=pg_env, user=user, password=password),
                warn_only=True, quiet=QUIET)

            if not 'CREATE ROLE' in create_user_result:
                if is_local_environment():
                    raise RuntimeError(u'Is your local user account `{0}` a '
                                       u'PostgreSQL administrator? it shoud '
                                       u'be. To acheive it, please '
                                       u'run:{1}'.format(
                                           pwd.getpwuid(os.getuid()).pw_name,
                                           '''
    sudo su - postgres
    USER=<your-username-here>
    PASS=<your-password-here>
    createuser --login --no-inherit --createdb --createrole --superuser ${USER}
    echo "ALTER USER ${USER} WITH ENCRYPTED PASSWORD '${PASS}';" | psql
    [exit]

To avoid invisible password interactions via Fabric/psql,
you should also setup the following in /etc/···/pg_hba.conf:

local    all    <MYUSERNAME>    trust

'''))
                else:
                    # NOTE: template0 is OK on linux, but not available on OSX.
                    raise RuntimeError(u'Your remote system lacks a dedicated '
                                       u'PostgreSQL administrator account. '
                                       u'Did you create one? You can specify '
                                       u'it via environment variables '
                                       u'$SPARKS_PG_SUPERUSER and '
                                       u'$SPARKS_PG_SUPERPASS. You can also '
                                       u'specify $SPARKS_PG_TMPL_DB (defaults '
                                       u' to “template1” if unset, which is '
                                       u'safe).')

        else:
            pg.wrapped_sudo(pg.ALTER_USER.format(pg_env=pg_env,
                            user=user, password=password), quiet=QUIET)

        if pg.wrapped_sudo(pg.SELECT_DB.format(pg_env=pg_env,
                           db=db), quiet=QUIET).strip() == '':
            pg.wrapped_sudo(pg.CREATE_DB.format(pg_env=pg_env,
                            db=db, user=user), quiet=QUIET)

    LOGGER.info('Done checking database setup.')


@task(task_class=DjangoTask)
def syncdb():
    """ Run the Django syncdb management command.

    .. todo:: avoid if Django >= 1.7 (obsolete).
    """

    with activate_venv():
        with cd(env.root):
            # TODO: this should be managed by git and the developers, not here.
            run('chmod 755 manage.py', quiet=QUIET)

    django_manage('syncdb --noinput')


@task(alias='migrate_task')
@with_remote_configuration
def migrate_task(remote_configuration=None, args=None):
    """ Run the Django migrate management command, and the Transmeta one.

    (only if ``django-transmeta`` is installed).

    .. versionchanged:: in 1.16 the function checks if ``transmeta`` is
        installed remotely and runs the command properly. before, it just
        ran the command inconditionnaly with ``warn_only=True``, which
        was less than ideal in case of a problem because the fab procedure
        didn't stop.
    """

    # Sometimes, we've got:
    #
    # [1flow.io] out: The following content types are stale and need to be deleted: # NOQA
    # [1flow.io] out:
    # [1flow.io] out:     core | articlesstatistic
    # [1flow.io] out:
    # [1flow.io] out: Any objects related to these content types by a foreign key will also # NOQA
    # [1flow.io] out: be deleted. Are you sure you want to delete these content types? # NOQA
    # [1flow.io] out: If you're unsure, answer 'no'.
    # [1flow.io] out:
    #
    # And this completely stops the migration process, because Fabric
    # can't seem to get the terminal and I cannot type "yes" anywhere.

    django_manage('migrate ' + (args or ''), prefix='yes yes | ')

    if 'transmeta' in remote_configuration.django_settings.INSTALLED_APPS:
        django_manage('sync_transmeta_db', prefix='yes | ')


@task(task_class=DjangoTask)
def migrate(args=None):
    """ The sparks wrapper for Fabric's migrate_task. """

    execute_or_not(migrate_task, args=args, sparks_roles=('db', 'pg', ))


@task(task_class=DjangoTask, alias='static')
def collectstatic(fast=True):
    """ The sparks wrapper for Fabric's collectstatic_task. """

    execute_or_not(collectstatic_task, fast=fast, sparks_roles=('web', ))


@with_remote_configuration
def collectstatic_task(remote_configuration=None, fast=True):
    """ Run the Django collectstatic management command.

    If :param:`fast` is ``False``, the ``STATIC_ROOT`` will be erased first.
    """

    if remote_configuration.django_settings.DEBUG:
        LOGGER.info('NOT running collectstatic on %s because `DEBUG=True`.',
                    env.host_string)
        return

    if not fast:
        with cd(env.root):
            run('rm -rf "{0}"'.format(
                remote_configuration.django_settings.STATIC_ROOT), quiet=QUIET)

    django_manage('collectstatic --noinput')


# ••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Direct-target tasks


def putdata_task(filename=None, confirm=True, **kwargs):

    if filename is None:
        filename = get_all_fixtures(order_by='date')[0]

        if confirm:
            prompt('OK to load {0} ([enter] or Control-C)?'.format(filename))

    remote_file = list(put(filename))[0]

    django_manage('loaddata {0}'.format(remote_file))


@task(task_class=DjangoTask)
def putdata(filename=None, confirm=True):
    """ Load a local fixture on the remote via Django's ``loaddata`` command.
    """

    # re-wrap the internal task via execute() to catch roledefs.
    execute_or_not(putdata_task, filename=filename, confirm=confirm,
                   sparks_roles=('db', ))


def getdata_task(app_model, filename=None, **kwargs):

    if filename is None:
        filename = new_fixture_filename(app_model)
        print('Dump data stored in {0}'.format(filename))

    with open(filename, 'w') as f:
        f.write(django_manage(
            'dumpdata {0} --indent 4 --format json --natural'.format(app_model),
            combine_stderr=False))


@task(task_class=DjangoTask)
def getdata(app_model, filename=None):
    """ Get a dump or remote data in a local fixture,
        via Django's ``dumpdata`` management command.

        Examples::

            # more or less abstract examples
            fab test getdata:myapp.MyModel
            fab production custom_settings getdata:myapp.MyModel

            # The 1flowapp.com landing page.
            fab test oneflowapp getdata:landing.LandingContent

        .. versionadded:: 1.16
    """

    # re-wrap the internal task via execute() to catch roledefs.
    execute_or_not(getdata_task, app_model=app_model,
                   filename=filename, sparks_roles=('db', ))


@task(aliases=('maintenance', 'maint', ))
def maintenance_mode(fast=True):
    """ Trigger maintenance mode (and restart services). """

    result = execute_or_not(maintenance_mode_task, fast=fast,
                            sparks_roles=('web', ))

    if result is None:
        return

    if any(result.values()):
        restart_services(fast=fast)


@task
def maintenance_mode_task(fast):

    with cd(env.root):
        if exists('MAINTENANCE_MODE'):
            LOGGER.info('Already in maintenance mode, not restarting services.')
            return False

        run('touch MAINTENANCE_MODE', quiet=QUIET)
        return True


@task(aliases=('operational', 'op', 'normal', 'resume', 'run', ))
def operational_mode(fast=True):
    """ Get out of maintenance mode (and restart services). """

    result = execute_or_not(operational_mode_task, fast=fast,
                            sparks_roles=('web', ))

    if result is None:
        return

    if any(result.values()):
        restart_services(fast=fast)


@task
def operational_mode_task(fast):

    with cd(env.root):
        if exists('MAINTENANCE_MODE'):
            run('rm -f  MAINTENANCE_MODE', quiet=QUIET)
            return True
        else:
            LOGGER.info('Already in operational mode, not restarting services.')
            return False


# ••••••••••••••••••••••••••••••••••••••••••••••••••••••• Deployment meta-tasks


def services_action(fast=False, action=None):
    """ Restart all remote services (nginx, gunicorn, celery…) in one task. """

    if is_local_environment():
        LOGGER.warning('Not acting on services, this is a local environment '
                       'and should be managed via Honcho.')
        return

    if action is None:
        action = 'status'

    execute_or_not(service_action_nginx, fast=fast,
                   action=action, sparks_roles=('load', ))

    execute_or_not(service_action_webserver_gunicorn, fast=fast,
                   action=action, sparks_roles=('web', ))

    # NOTE: 'web' is already done (just before)
    roles_to_act_on = worker_roles[:] + ['beat', 'flower', 'shell']

    # Run this multiple time, for each role:
    # each of them has a dedicated supervisor configuration,
    # even when running on the same machine.
    # Degrouping role execution ensures execute_or_not() gets an unique
    # role for each host it will execute on. This is a limitation of the
    # the execute_or_not() function.
    for role in roles_to_act_on:
        execute_or_not(service_action_worker_celery, fast=fast,
                       action=action, sparks_roles=(role, ))


@task(alias='restart')
def restart_services(fast=False):

    services_action(fast=fast, action='restart')


@task(alias='stop')
def stop_services(fast=True):
    """ stop all remote services (nginx, gunicorn, celery…) in one task. """

    services_action(fast=fast, action='stop')


@task(alias='start')
def start_services(fast=True):
    """ start all remote services (nginx, gunicorn, celery…) in one task. """

    services_action(fast=fast, action='start')


@task(alias='status')
def status_services(fast=True):
    """ Get all remote services status (nginx, gunicorn, celery…) at once. """

    services_action(fast=fast, action='status')


@task(alias='remove')
def remove_services(fast=True):
    """ remove all services files configuration in one task. """

    services_action(fast=fast, action='remove')


@task(aliases=('initial', ))
def runable(fast=False, upgrade=False):
    """ Ensure we can run the {web,dev}server: db+req+sync+migrate+static. """

    if not fast:
        # Ensure Git is installed.
        execute_or_not(fabfile.dev_mini, sparks_roles=('__any__', ))

        execute_or_not(init_environment, sparks_roles=('__any__', ))

        execute_or_not(install_components, upgrade=upgrade,
                       sparks_roles=('__any__', ))


    # Push everything first.
    # Don't fail if local user doesn't have my aliases.
    local('git upa || git up || git pa || git push', capture=QUIET)

    if not is_local_environment():
        push_environment()  # already wraps execute_or_not()

        git_update()  # already wraps execute_or_not()

        if not is_production_environment():
            # fast or not, we must catch this one to
            # avoid source repository desynchronization.
            execute_or_not(push_translations, sparks_roles=('lang', ))

        git_pull()  # already wraps execute_or_not()

    git_clean()  # already wraps execute_or_not()

    requirements(fast=fast, upgrade=upgrade)  # already wraps execute_or_not()

    compilemessages()  # already wraps execute_or_not()

    collectstatic(fast=fast)

    #
    # TODO: add 'mysql' and others.
    #

    if not fast:
        execute_or_not(createdb, sparks_roles=('db', 'pg', ))

    # TODO: test if Django 1.7+, and don't run in this case.
    execute_or_not(syncdb, sparks_roles=('db', 'pg', ))

    migrate()  # already wraps execute_or_not()


@task(aliases=('fast', 'fastdeploy', ))
def fast_deploy(upgrade=True):
    """ Deploy FAST! For templates / static changes only. """

    # not our execute_or_not(), here we want Fabric
    # to handle its classic execution model.
    execute(deploy, fast=True, upgrade=upgrade)


@task(default=True, aliases=('fulldeploy', 'full_deploy', ))
def deploy(fast=False, upgrade=False):
    """ Pull code, ensure runable, restart services. """

    has_worker = False

    for role in env.roledefs:
        if role in worker_roles:
            has_worker = True

    if (has_worker and len(env.roledefs.get('beat', [])) == 0
        ) and not env.get('sparks_options', {}).get(
            'no_warn_for_missing_beat', False):
        raise RuntimeError("You must define a 'beat' roledef if "
                           "you plan to run any Celery worker.")

    # not our execute_or_not(), here we want Fabric
    # to handle its classic execution model.
    execute(runable, fast=fast, upgrade=upgrade)

    # not our execute_or_not(), here we want Fabric
    # to handle its classic execution model.
    execute(restart_services, fast=fast)


@task(aliases=('roles', 'cherry-pick-role', 'cherry-pick-roles',
      'pick-role', 'pick-roles', 'R'))
def role(*roles):
    """ clean the current roledefs to keep only the role(s) picked here,
        to be able to deploy them one by one without disturbing the others.
        Eg, to remove a queue from only 2 workers (out of any number)::

            fab production role:worker_role pick:w01.domain,w02.domain remove


        .. warning:: use with caution and at your own risk!

        .. this task exists because the
            plain ``fab production -R worker_role -H … …`` won't
            work as expected. `Fabric` will not pick the ``env.roledefs``
            set by the ``production`` task to select ``-R`` from. I don't
            known if it's a bug of a feature, but anyway this tasks justs
            solves this problem.

        .. versionadded:: 3.6

    """

    LOGGER.debug(u'before role-picking: env.roledefs=%s roles=%s',
                 env.roledefs.keys(), roles)

    # Don't use 'in env.roledefs', or only if you want to hit
    # 'RuntimeError: dictionary changed size during iteration'
    for role in env.roledefs.keys():
        if role in roles:
            continue

        del env.roledefs[role]

    # This special case requires a special patch ;-)
    if len(env.roledefs.get('beat', [])) == 0:
        sparks_options = getattr(env, 'sparks_options', {})
        sparks_options['no_warn_for_missing_beat'] = True
        env.sparks_options = sparks_options

    LOGGER.debug('after role-picking: env.roledefs=%s', env.roledefs.keys())


@task(aliases=('cherry-pick', 'select', 'hosts', 'H'))
def pick(*machines):
    """ clean the current roledefs to keep only the machines picked here,
        to be able to deploy them one by one without disturbing the others.
        Eg, to add 2 new workers to an already running set of machines::

            fab production pick:new_worker.domain,other_new.domain deploy


        .. warning:: use with caution and at your own risk! You should
            deploy exactly the same version of your code on the picked
            machines. But if you use this task, you already know this.

        .. this task exists because the
            plain ``fab production -H new_worker.domain deploy`` won't
            work as expected. `Fabric` will empty ``env.roledefs`` if
            you use ``-H``. I don't known if it's a bug of a feature,
            but anyway this tasks justs solves this problem.

        .. versionadded:: 3.5

        .. versionchanged:: in 3.5.1, the ``H`` task alias was added,
            to be able to write ``fab prod H:my_worker deploy``, which
            ressembles enough to ``fab prod -H my_worker deploy`` for
            ``@bitprophet`` not to notice this current workaround task
            if he reads too fast. Jeff, I just **loooove** ``Fabric`` ;-)
    """

    LOGGER.debug('before machines-picking: env.roledefs=%s machines=%s',
                 env.roledefs.keys(), machines)

    if len(machines) == 1:
        # Avoid messing with my fabfile switching
        # this on and off everytime something fails.
        env.parallel = False

    for role, hosts in env.roledefs.items():
        new_hosts_for_role = []
        for machine in hosts:
            if machine in machines:
                new_hosts_for_role.append(machine)
        env.roledefs[role] = new_hosts_for_role

    # This special case requires a special patch ;-)
    if len(env.roledefs.get('beat', [])) == 0:
        sparks_options = getattr(env, 'sparks_options', {})
        sparks_options['no_warn_for_missing_beat'] = True
        env.sparks_options = sparks_options

    LOGGER.debug('after machines-picking: env.roledefs=%s',
                 env.roledefs.keys())
