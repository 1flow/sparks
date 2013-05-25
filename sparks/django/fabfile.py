# -*- coding: utf-8 -*-
"""
    Fabric common rules for a Django project.


"""

import os
import logging
import datetime

try:
    from fabric.api              import env, run, sudo, task, local
    from fabric.tasks            import Task
    from fabric.operations       import put, prompt
    from fabric.contrib.files    import exists, upload_template
    from fabric.context_managers import cd, prefix, settings

except ImportError:
    print('>>> FABRIC IS NOT INSTALLED !!!')
    raise

from ..fabric import (fabfile, with_remote_configuration,
                      local_configuration as platform,
                      is_local_environment,
                      is_development_environment,
                      is_production_environment)
from ..pkg import brew
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
env.requirements_file     = 'config/requirements.txt'
env.dev_requirements_file = 'config/dev-requirements.txt'
env.branch                = '<GIT-FLOW-DEPENDANT>'
env.use_ssh_config        = True


# ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Django task
class DjangoTask(Task):
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


@task(aliases=('base', 'base_components'))
@with_remote_configuration
def install_components(remote_configuration=None, upgrade=False):
    """ Install necessary packages to run a full Django stack.

        .. todo:: split me into packages/modules where appropriate.

        .. todo:: split me into server (PG) and clients (PG-dev) packages.
    """

    fabfile.dev()
    fabfile.dev_web()
    fabfile.dev_django_full()

    # OSX == test environment == no nginx/supervisor/etc
    if remote_configuration.is_osx:
        brew.brew_add(('redis', 'memcached', 'libmemcached', ))

        run('ln -sfv /usr/local/opt/redis/*.plist ~/Library/LaunchAgents')
        run('launchctl load ~/Library/LaunchAgents/homebrew.*.redis.plist')

        run('ln -sfv /usr/local/opt/memcached/*.plist ~/Library/LaunchAgents')
        run('launchctl load ~/Library/LaunchAgents/homebrew.*.memcached.plist')

        print('NO WEB-SERVER installed, assuming this is a dev machine.')

    else:
        #apt.apt_add(('python-pip', 'supervisor', 'nginx-full',))
        #apt.apt_add(('redis-server', 'memcached', ))

        # fabfile.sys_django(env.sys_components
        #                    if hasattr(env, 'sys_components')
        #                    else '')
        #fabfile.dev_django_full()
        #fabfile.dev_memcache()
        pass

# ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Helpers


def get_git_branch():
    """ Return either ``env.branch`` if defined, else ``master`` if environment
        is ``production``, or ``develop`` if anything else than ``production``
        (we use the :program:`git-flow` branching model). """

    branch = env.branch

    if branch == '<GIT-FLOW-DEPENDANT>':
        branch = 'master' if env.environment == 'production' else 'develop'

    return branch


def activate_venv():

    return prefix('workon %s' % env.virtualenv)


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
        it they do not exist. """

    if not exists(env.root):
        run('mkdir -p "{0}"'.format(os.path.dirname(env.root)))

        prompt(u'Please create the git repository in {0}:{1} and press '
               u'[enter] when done.'.format(env.host_string, env.root))

    if run('lsvirtualenv | grep {0}'.format(env.virtualenv),
           warn_only=True).strip() == '':
        run('mkvirtualenv {0}'.format(env.virtualenv))


@task(alias='req')
def requirements(fast=False, upgrade=False):
    """ Install PIP requirements (and dev-requirements).

        .. note:: :param:`fast` is not used yet, but exists for consistency
            with other fab tasks which handle it.
    """

    if upgrade:
        command = 'pip install -U'
    else:
        command = 'pip install'

    with cd(env.root):
        with activate_venv():
            if is_development_environment():
                dev_req = os.path.join(env.root, env.dev_requirements_file)

                # exists(): we are looking for a remote file!
                if not exists(dev_req):
                    dev_req = os.path.join(os.path.dirname(__file__),
                                           'dev-requirements.txt')
                    #TODO: "put" it there !!

                run("{sparks_env}{django_env}{command} "
                    "--requirement {requirements_file}".format(
                    sparks_env=sparks_djsettings_env_var(),
                    django_env=django_settings_env_var(),
                    command=command, requirements_file=dev_req))

            req = os.path.join(env.root, env.requirements_file)

            # exists(): we are looking for a remote file!
            if not exists(req):
                req = os.path.join(os.path.dirname(__file__),
                                   'requirements.txt')
                #TODO: "put" it on the remote side !!

            run("{sparks_env}{django_env}{command} "
                "--requirement {requirements_file}".format(
                sparks_env=sparks_djsettings_env_var(),
                django_env=django_settings_env_var(),
                command=command, requirements_file=req))


@task(alias='pull')
def git_update():

    # TODO: git up?

    # Push everything first. This is not strictly mandatory.
    # Don't fail if local user doesn't have my `pa` alias.
    local('git pa || true')

    with cd(env.root):
        if not is_local_environment():
            run('git checkout %s' % get_git_branch())


@task(alias='pull')
def git_pull():

    with cd(env.root):
        if not run('git pull').strip().endswith('Already up-to-date.'):
            # reload the configuration to refresh Django settings.
            # TODO: examine commits HERE and in push_translations()
            # to reload() only if settings/* changed.
            #
            # We import it manually here, to avoid using the
            # @with_remote_configuration decorator, which would imply
            # implicit fetching of Django settings. On first install/deploy,
            # this would fail because requirements are not yet installed.
            try:
                from ..fabric import remote_configuration
                remote_configuration.reload()

            except:
                LOGGER.exception('Cannot reload remote_settings! '
                                 '(you can safely ignore this warning on '
                                 'first deploy)')


@task(alias='getlangs')
@with_remote_configuration
def push_translations(remote_configuration=None):

    if not remote_configuration.django_settings.DEBUG:
        # remote translations are fetched only on development / test
        # environments. Production are not meant to host i18n work.
        return

    with cd(env.root):
        if run("git status | grep -E 'modified:.*locale.*django.po' "
               "|| true") != '':
            run(('git add -u \*locale\*po '
                '&& git commit -m "{0}" '
                # If there are pending commits in the central, `git push` will
                # fail if we don't pull them prior to pushing local changes.
                '&& (git up || git pull) && git push').format(
                'Automated l10n translations from {0} on {1}.').format(
                env.host_string, datetime.datetime.now().isoformat()))

            # Get the translations changes back locally.
            # Don't fail if the local user doesn't have git-up,
            # and try to pull the standard way.
            local('git up || git pull')


# •••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Services


@task(alias='nginx')
def restart_nginx(fast=False):

    if not exists('/etc/nginx'):
        return

    # Nothing more for now, the remaining is disabled.
    return

    if not exists('/etc/nginx/sites-available/beau-dimanche.com'):
        #put('config/nginx-site.conf', '')
        pass

    if not exists('/etc/nginx/sites-enabled/beau-dimanche.com'):
        with cd('/etc/nginx/sites-enabled/'):
            sudo('ln -sf ../sites-available/beau-dimanche.com')


@task(alias='celery')
def restart_celery_service(fast=False):
    """ Restart celery (only if detected as installed). """

    if exists('/etc/init.d/celeryd'):
        sudo("/etc/init.d/celeryd restart")


def build_supervisor_program_name():
    """ Returns a tuple: a boolean and a program name.

        The boolean indicates if the fabric `env` has
        the :attr:`sparks_djsettings` attribute, and the program name
        will be somewhat unique, built from ``env.project``,
        ``env.sparks_djsettings`` if it exists and ``env.environment``.

    """

    # We need something more unique than project, in case we have
    # many environments on the same remote machine. And alternative
    # settings, too, because we will have a supervisor process for them.
    if hasattr(env, 'sparks_djsettings'):
        return True, '{0}_{1}_{2}'.format(env.project,
                                          env.sparks_djsettings,
                                          env.environment)

    else:
        return False, '{0}_{1}'.format(env.project, env.environment)


def supervisor_add_environment(context, has_djsettings):
    """ Helper function: add (or not) an ``environment`` item
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
        context['environment'] = 'environment={0}'.format(','.join(env_vars))

    else:
        # The item must exist, else the templating engine will raise an error.
        context['environment'] = ''


def handle_supervisor_config(supervisor, remote_configuration):
    """ Helper function: Upload an environment-specific and auto-generated
        supervisor configuration file. Update/restart supervisor
        only if one of the files changed.
    """

    superconf = os.path.join(platform.django_settings.BASE_ROOT,
                             'config',
                             'gunicorn_supervisor_{0}.conf'.format(
                             supervisor.program_name))

    # os.path.exists(): we are looking for a LOCAL file,
    # in the current Django project. Devops can prepare a
    # fully custom supervisor configuration file for the
    # Django web worker.
    if not os.path.exists(superconf):
        # If full-custom isn't present,
        # create a sparks-crafted template.
        superconf = os.path.join(os.path.dirname(__file__),
                                 'gunicorn_supervisor.template')

    destination = '/etc/supervisor/conf.d/{0}.conf'.format(
        supervisor.program_name)

    context = {
        'env': env.environment,
        'root': env.root,
        'user': env.user,
        'branch': env.branch,
        'project': env.project,
        'program': supervisor.program_name,
        'user_home': env.user_home
            if hasattr(env, 'user_home')
            else remote_configuration.tilde,
        'virtualenv': env.virtualenv,
    }

    supervisor_add_environment(context, supervisor.has_djsettings)

    if exists(destination):
        upload_template(superconf, destination + '.new',
                        context=context, use_sudo=True, backup=False)

        if sudo('diff {0} {0}.new'.format(destination)) == '':
            sudo('rm -f {0}.new'.format(destination))

        else:
            sudo('mv {0}.new {0}'.format(destination))
            supervisor.update  = True
            supervisor.restart = True

    else:
        upload_template(superconf, destination, context=context,
                        use_sudo=True, backup=False)
        # No need to restart, the update will
        # add the new program and start it
        # automatically, thanks to supervisor.
        supervisor.update = True


def handle_gunicorn_config(supervisor):
    """ Helper function: upload a default gunicorn configuration file
        if there is none in the project (else, the one
        from the project will be automatically used).
    """

    guniconf = os.path.join(
        platform.django_settings.BASE_ROOT,
        'config/gunicorn_conf_{0}.py'.format(
        supervisor.program_name))

    # os.path.exists(): we are looking for a LOCAL file in the
    # Django project, that will be used remotely if present,
    # once code is synchronized.
    if not os.path.exists(guniconf):
        guniconf = os.path.join(os.path.dirname(__file__),
                                'gunicorn_conf_default.py')

    gunidest = os.path.join(env.root,
                            'config/gunicorn_conf_{0}.py'.format(
                            supervisor.program_name))

    if exists(gunidest):
        put(guniconf, gunidest + '.new')

        if sudo('diff {0} {0}.new'.format(gunidest)) == '':
            sudo('rm -f {0}.new'.format(gunidest))

        else:
            sudo('mv {0}.new {0}'.format(gunidest))
            supervisor.update  = True
            supervisor.restart = True

    else:
        # copy the default configuration to remote.
        # WARNING/NOTE: it will be put in the remote git working
        # directory. This *will* trigger a conflict if a specific
        # configuration file is added afterwards by the developers,
        # and they'll need to delete it manually before restarting
        # the whole deploy operation. I know this isn't cool.
        put(guniconf, gunidest)

        if not supervisor.update:
            supervisor.restart = True


@task(task_class=DjangoTask, alias='gunicorn')
@with_remote_configuration
def restart_gunicorn_supervisor(remote_configuration=None, fast=False):
    """ (Re-)upload configuration files and reload gunicorn via supervisor.

        This will reload only one service, even if supervisor handles more
        than one on the remote server. Thus it's safe for production to
        reload test :-)

    """

    if exists('/etc/supervisor'):

        has_djsettings, program_name = build_supervisor_program_name()

        supervisor = SimpleObject(from_dict={
                                  'update': False,
                                  'restart': False,
                                  'has_djsettings': has_djsettings,
                                  'program_name': program_name
                                  })

        if not fast:
            handle_supervisor_config(supervisor, remote_configuration)
            handle_gunicorn_config(supervisor)

        # cf. http://stackoverflow.com/a/9310434/654755

        if supervisor.update:
            # This will start /
            sudo("supervisorctl update")

            if supervisor.restart:
                sudo("supervisorctl restart {0}".format(program_name))

        else:
            # In any case, we restart the process during a {fast}deploy,
            # to reload the Django code even if configuration hasn't changed.
            sudo("supervisorctl restart {0}".format(program_name))


# ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Django specific

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
            return run('{0}{1}./manage.py {2}'.format(
                       prefix, sparks_djsettings_env_var(), command), **kwargs)


@with_remote_configuration
def handlemessages(remote_configuration=None, mode=None):
    """ Run the Django compilemessages management command. """

    if mode is None:
        mode = 'make'

    elif mode not in ('make', 'compile'):
        raise RuntimeError(
            '"mode" argument must be either "make" or "compile".')

    def compile_internal(run_from):
        for language in languages:
            run('{0}{1}./manage.py {2}messages --locale {3}'.format(
                sparks_djsettings_env_var(), run_from, mode, language))

    # Transform language codes (eg. 'fr-fr') to locale names (eg. 'fr_FR'),
    # keeping extensions (eg. '.utf-8'), but don't touch short codes (eg. 'en').
    languages = [('{0}_{1}{2}'.format(code[:2], code[3:5].upper(), code[5:])
                 if len(code) > 2 else code) for code, name
                 in remote_configuration.django_settings.LANGUAGES
                 if code != remote_configuration.django_settings.LANGUAGE_CODE]

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
                            compile_internal(run_from='../../')


@task(task_class=DjangoTask, alias='messages')
def makemessages():
    handlemessages(mode='make')


@task(task_class=DjangoTask, alias='compile')
def compilemessages():
    handlemessages(mode='compile')


@task(task_class=DjangoTask)
def syncdb():
    """ Run the Django syndb management command. """

    with activate_venv():
        with cd(env.root):
            # TODO: this should be managed by git and the developers, not here.
            run('chmod 755 manage.py', quiet=True)

    django_manage('syncdb --noinput')


@task(task_class=DjangoTask)
@with_remote_configuration
def migrate(remote_configuration=None, args=None):
    """ Run the Django migrate management command, and the Transmeta one
        if ``django-transmeta`` is installed.

        .. versionchanged:: in 1.16 the function checks if ``transmeta`` is
            installed remotely and runs the command properly. before, it just
            ran the command inconditionnaly with ``warn_only=True``, which
            was less than ideal in case of a problem because the fab procedure
            didn't stop.
    """

    django_manage('migrate ' + (args or ''))

    if 'transmeta' in remote_configuration.django_settings.INSTALLED_APPS:
        django_manage('sync_transmeta_db', prefix='yes | ')


@task(task_class=DjangoTask, alias='static')
def collectstatic():
    """ Run the Django collectstatic management command. """

    django_manage('collectstatic --noinput')


@task(task_class=DjangoTask)
def putdata(filename=None, confirm=True):
    """ Put a local fixture on the remote end with via transient filename
        and load it via Django's ``loaddata`` command.

        :param
    """

    if filename is None:
        filename = get_all_fixtures(order_by='date')[0]

        if confirm:
            prompt('OK to load {0} ([enter] or Control-C)?'.format(filename))

    remote_file = list(put(filename))[0]

    django_manage('loaddata {0}'.format(remote_file))


@task(task_class=DjangoTask)
def getdata(app_model, filename=None):
    """ Get a dump or remote data in a local fixture, via
        Django's ``dumpdata`` management command.

        Examples::

            # more or less abstract examples
            fab test getdata:myapp.MyModel
            fab production custom_settings getdata:myapp.MyModel

            # The 1flowapp.com landing page.
            fab test oneflowapp getdata:landing.LandingContent

        .. versionadded:: 1.16
    """

    if filename is None:
        filename = new_fixture_filename(app_model)
        print('Dump data will be stored in {0}.'.format(filename))

    with open(filename, 'w') as f:
        f.write(django_manage('dumpdata {0} --indent 4 '
                '--format json --natural'.format(app_model), quiet=True))

# ••••••••••••••••••••••••••••••••••••••••••••••••••••••• Deployment meta-tasks


@task(aliases=('maintenance', 'maint', ))
@with_remote_configuration
def maintenance_mode(remote_configuration=None, fast=True):
    """ Trigger maintenance mode (and restart services). """

    djsettings = getattr(remote_configuration, 'django_settings', None)

    print ('>> %s' % djsettings.BASE_ROOT)

    with cd(djsettings.BASE_ROOT):
        run('touch MAINTENANCE_MODE')

    restart_services(fast=fast)


@task(aliases=('operational', 'op', 'normal', 'resume', 'run', ))
@with_remote_configuration
def operational_mode(remote_configuration=None, fast=True):
    """ Get out of maintenance mode (and restart services). """

    djsettings = getattr(remote_configuration, 'django_settings', None)

    with cd(djsettings.BASE_ROOT):
        run('rm -f MAINTENANCE_MODE')

    restart_services(fast=fast)


@task(task_class=DjangoTask)
@with_remote_configuration
def createdb(remote_configuration=None, db=None, user=None, password=None,
             installation=False):
    """ Create the PostgreSQL user & database if they don't already exist.
        Install PostgreSQL on the remote system if asked to. """

    if installation:
        from ..fabric import fabfile
        fabfile.db_postgresql()

    db, user, password = pg.temper_db_args(db=db, user=user, password=password)

    if is_local_environment():
        pg_env = []

    else:
        pg_env = ['PGUSER={0}'.format(env.pg_superuser)
                  if hasattr(env, 'pg_superuser') else '',
                  'PGPASSWORD={0}'.format(env.pg_superpass)
                  if hasattr(env, 'pg_superpass') else '']

    pg_env.append('PGDATABASE={0}'.format(env.pg_superdb
                  if hasattr(env, 'pg_superdb')
                  else 'template1'))

    djsettings = getattr(remote_configuration, 'django_settings', None)

    if djsettings is not None:
        db_setting = djsettings.DATABASES['default']
        db_host    = db_setting.get('HOST', None)
        db_port    = db_setting.get('PORT', None)

        if db_host is not None:
            pg_env.append('PGHOST={0}'.format(db_host))

        if db_port is not None:
            pg_env.append('PGPORT={0}'.format(db_port))

    # flatten the list
    pg_env = ' '.join(pg_env)

    with settings(sudo_user=pg.get_admin_user()):
        if sudo(pg.SELECT_USER.format(
                pg_env=pg_env, user=user)).strip() == '':
            sudo(pg.CREATE_USER.format(
                 pg_env=pg_env, user=user, password=password))
        else:
            sudo(pg.ALTER_USER.format(pg_env=pg_env,
                 user=user, password=password))

        if sudo(pg.SELECT_DB.format(pg_env=pg_env, db=db)).strip() == '':
            sudo(pg.CREATE_DB.format(pg_env=pg_env, db=db, user=user))


@task(alias='restart')
def restart_services(fast=False):
    restart_nginx(fast=fast)
    restart_celery_service(fast=fast)
    restart_gunicorn_supervisor(fast=fast)


@task(aliases=('initial', ))
def runable(fast=False, upgrade=False):
    """ Ensure we can run the {web,dev}server: db+req+sync+migrate+static. """

    if not is_local_environment():

        if not fast:
            init_environment()

        git_update()

        if not is_production_environment():
            # fast or not, we must catch this one to
            # avoid source repository desynchronization.
            push_translations()

        git_pull()

    requirements(fast=fast, upgrade=upgrade)

    if not fast:
        createdb()

    syncdb()
    migrate()
    compilemessages()

    if not is_local_environment():
        # In debug mode, Django handles the static contents via a dedicated
        # view. We don't need to create/refresh/maintain the global static/ dir.
        collectstatic()


@task(aliases=('fast', 'fastdeploy', ))
def fast_deploy():
    """ Deploy FAST! For templates / static changes only. """

    deploy(fast=True)


@task(default=True, aliases=('fulldeploy', 'full_deploy', ))
def deploy(fast=False, upgrade=False):
    """ Pull code, ensure runable, restart services. """

    if not fast:
        install_components(upgrade=upgrade)

    runable(fast=fast, upgrade=upgrade)

    restart_services(fast=fast)
