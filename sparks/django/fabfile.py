# -*- coding: utf-8 -*-
"""
    Fabric common rules for a Django project.


"""

import os
import logging

try:
    from fabric.api              import env, run, sudo, task, local
    from fabric.operations       import put, prompt
    from fabric.contrib.files    import exists, upload_template
    from fabric.context_managers import cd, prefix, settings

except ImportError:
    print('>>> FABRIC IS NOT INSTALLED !!!')
    raise

from ..django      import is_local_environment
from ..fabric      import (fabfile, with_remote_configuration,
                           local_configuration as platform)
from ..pkg         import brew
from ..foundations import postgresql as pg

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


@task(aliases=('base', 'base_components'))
@with_remote_configuration
def install_components(remote_configuration=None, upgrade=False):
    """ Install necessary packages to run a full Django stack.

        .. todo:: split me into packages/modules where appropriate.

        .. todo:: split me into server (PG) and clients (PG-dev) packages.
    """

    fabfile.dev()

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
def requirements(upgrade=False):
    """ Install PIP requirements (and dev-requirements). """

    if upgrade:
        command = 'pip install -U'
    else:
        command = 'pip install'

    fabfile.dev()
    fabfile.dev_django_full()

    with cd(env.root):
        with activate_venv():

            if is_local_environment():
                dev_req = os.path.join(env.root, env.dev_requirements_file)

                # exists(): we are looking for a remote file!
                if not exists(dev_req):
                    dev_req = os.path.join(os.path.dirname(__file__),
                                           'dev-requirements.txt')
                    #TODO: "put" it there !!

                run("{command} --requirement {requirements_file}".format(
                    command=command, requirements_file=dev_req))

            req = os.path.join(env.root, env.requirements_file)

            # exists(): we are looking for a remote file!
            if not exists(req):
                req = os.path.join(os.path.dirname(__file__),
                                   'requirements.txt')
                #TODO: "put" it on the remote side !!

            run("{command} --requirement {requirements_file}".format(
                command=command, requirements_file=req))


@task(alias='pull')
def git_pull():

    # Push everything first. This is not strictly mandatory.
    # Don't fail if local user doesn't have my `pa` alias.
    local('git pa || true')

    branch = env.branch

    if branch == '<GIT-FLOW-DEPENDANT>':
        branch = 'master' if env.environment == 'production' else 'develop'

    with cd(env.root):
        if not is_local_environment():
            run('git checkout %s' % branch)

        run('git pull')


def activate_venv():

    return prefix('workon %s' % env.virtualenv)


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
    """ Add (or not) an ``environment`` item to :param:`context`, given
        the current Fabric ``env``.

        If :param:`has_djsettings` is ``True``, ``SPARKS_DJANGO_SETTINGS``
        will be added.

        If ``env`` has an ``environment_vars`` attributes, they are assumed
        to be a python list (eg.``[ 'KEY1=value', 'KEY2=value2' ]``) and
        will be inserted into context too, converted to supervisor
        configuration file format.
    """

    env_vars = []

    if has_djsettings:
        env_vars.append('SPARKS_DJANGO_SETTINGS={0}'.format(
                        env.sparks_djsettings))

    if hasattr(env, 'environment_vars'):
            env_vars.extend(env.environment_vars)

    if env_vars:
        context['environment'] = 'environment={0}'.format(','.join(env_vars))

    else:
        # The item must exist, else the templating engine will raise an error.
        context['environment'] = ''


@task(alias='gunicorn')
@with_remote_configuration
def restart_gunicorn_supervisor(remote_configuration=None, fast=False):
    """ (Re-)upload configuration files and reload gunicorn via supervisor.

        This will reload only one service, even if supervisor handles more
        than one on the remote server. Thus it's safe for production to
        reload test :-)

    """

    if exists('/etc/supervisor'):

        has_djsettings, program_name = build_supervisor_program_name()

        need_service_add = False

        if not fast:

            #
            # Upload an environment-specific and auto-generated
            # supervisor configuration file.
            #

            superconf = os.path.join(env.root, 'config',
                                     'gunicorn_supervisor_{0}.conf'.format(
                                     program_name))

            # os.path.exists(): we are looking for a LOCAL file, in sparks.
            if not os.path.exists(superconf):
                superconf = os.path.join(os.path.dirname(__file__),
                                         'gunicorn_supervisor.template')

            destination = '/etc/supervisor/conf.d/{0}.conf'.format(program_name)

            context = {
                'env': env.environment,
                'root': env.root,
                'user': env.user,
                'branch': env.branch,
                'project': env.project,
                'program': program_name,
                'user_home': env.user_home
                    if hasattr(env, 'user_home')
                    else remote_configuration.tilde,
                'virtualenv': env.virtualenv,
            }

            supervisor_add_environment(context, has_djsettings)

            if not exists(destination):
                need_service_add = True

            upload_template(superconf, destination, context=context,
                            use_sudo=True, backup=False)

            #
            # Upload a default gunicorn configuration file
            # if there is none in the project (else, the one
            # from the project will be automatically used).
            #

            local_config_file = os.path.join(
                platform.django_settings.PROJECT_ROOT,
                'config/gunicorn_conf_{0}.py'.format(
                program_name))

            # os.path.exists(): we are looking for a LOCAL file, that will
            # be used remotely if present, once code is synchronized.
            if not os.path.exists(local_config_file):
                unidefault = os.path.join(os.path.dirname(__file__),
                                          'gunicorn_conf_default.py')

                unidest = os.path.join(env.root,
                                       'config/gunicorn_conf_{0}.py'.format(
                                       program_name))

                # copy the default configuration to remote::specific.
                put(unidefault, unidest)

        #
        # Reload supervisor, it will restart gunicorn.
        #

        # cf. http://stackoverflow.com/a/9310434/654755

        if need_service_add:
            sudo("supervisorctl add {0} && supervisorctl start {0}".format(
                 program_name))

        else:
            # Just in case something went wrong between 2 fabric runs,
            # we reload. This is not strictly needed in normal conditions
            # but will allow recovering from bad situations without having
            # to repair things manually.
            sudo("supervisorctl reload "
                 "&& supervisorctl restart {0}".format(
                 program_name))


# ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Django specific

@task(alias='static')
def collectstatic():
    """ Run the Django collectstatic management command. """

    with cd(env.root):
        with activate_venv():
            run('{0}./manage.py collectstatic --noinput'.format(
                'SPARKS_DJANGO_SETTINGS={0} '.format(env.sparks_djsettings)
                if hasattr(env, 'sparks_djsettings') else ''))


@task
def syncdb():
    """ Run the Django syndb management command. """

    with cd(env.root):
        with activate_venv():
            run('chmod 755 manage.py', quiet=True)
            run('{0}./manage.py syncdb --noinput'.format(
                'SPARKS_DJANGO_SETTINGS={0} '.format(env.sparks_djsettings)
                if hasattr(env, 'sparks_djsettings') else ''))


@task
def migrate(*args):
    """ Run the Django migrate management command. """

    with cd(env.root):
        with activate_venv():
            run("{0}./manage.py migrate ".format(
                'SPARKS_DJANGO_SETTINGS={0} '.format(env.sparks_djsettings)
                if hasattr(env, 'sparks_djsettings') else '') + ' '.join(args))

            run('yes | {0}./manage.py sync_transmeta_db'.format(
                'SPARKS_DJANGO_SETTINGS={0} '.format(env.sparks_djsettings)
                if hasattr(env, 'sparks_djsettings') else ''), warn_only=True)


@task
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
                  if hasattr(env, 'pg_superuser') else '']

        pg_env.append('PGPASSWORD={0}'.format(env.pg_superpass)
                      if hasattr(env, 'pg_superpass') else '')

    pg_env.append('PGDATABASE={0}'.format(env.pg_superdb
                  if hasattr(env, 'pg_superdb')
                  else 'template1'))

    if hasattr(remote_configuration, 'django_settings'):
        db_setting = remote_configuration.django_settings.DATABASES['default']
        db_host    = db_setting.get('HOST', '')
        db_port    = db_setting.get('PORT', '')

        if db_host != '':
            pg_env.append('PGHOST={0}'.format(db_host))

        if db_port != '':
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


# ••••••••••••••••••••••••••••••••••••••••••••••••••••••• Deployment meta-tasks


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
        git_pull()

    if not fast:
        requirements(upgrade=upgrade)
        createdb()
        syncdb()
        migrate()

    collectstatic()


@task(aliases=('fast', 'fastdeploy', ))
def fast_deploy():
    """ Deploy FAST! For templates / static changes only. """

    deploy(fast=True)


@task
def deploy(fast=False, upgrade=False):
    """ Pull code, ensure runable, restart services. """

    if not fast:
        install_components(upgrade=upgrade)

    runable(fast=fast, upgrade=upgrade)

    restart_services(fast=fast)
