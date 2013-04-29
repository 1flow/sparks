# -*- coding: utf-8 -*-
"""
    Fabric common rules for a Django project.


"""

import os
import logging

try:
    from fabric.api              import env, run, sudo, task, local
    from fabric.operations       import put
    from fabric.contrib.files    import exists, upload_template
    from fabric.context_managers import cd, prefix, settings

except ImportError:
    print('>>> FABRIC IS NOT INSTALLED !!!')
    raise

from ..django      import is_local_environment
from ..fabric      import with_remote_configuration
from ..pkg         import apt, brew, pip
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
env.branch                = 'master'


@with_remote_configuration
def install_base(remote_configuration=None):
    """ Install necessary packages to run a full Django stack.
        .. todo:: split me into packages/modules where appropriate. """

    # OSX == test environment == no nginx/supervisor/etc
    if remote_configuration.is_osx:
        brew.brew_add(('redis', 'memcached', 'libmemcached', ))

        run('ln -sfv /usr/local/opt/redis/*.plist ~/Library/LaunchAgents')
        run('launchctl load ~/Library/LaunchAgents/homebrew.*.redis.plist')

        run('ln -sfv /usr/local/opt/memcached/*.plist ~/Library/LaunchAgents')
        run('launchctl load ~/Library/LaunchAgents/homebrew.*.memcached.plist')

    else:
        apt.apt_add(('python-pip', 'supervisor', 'nginx-full',))
        apt.apt_add(('redis-server', 'memcached', 'libmemcached-dev', ))
        apt.apt_add(('build-essential', 'python-all-dev', ))

    # This is common
    pip.pip2_add(('virtualenv', 'virtualenvwrapper', ))

    # Nothing more for now, the remaining is disabled.
    return

    if not exists('/etc/nginx/sites-available/beau-dimanche.com'):
        #put('config/nginx-site.conf', '')
        pass

    if not exists('/etc/nginx/sites-enabled/beau-dimanche.com'):
        with cd('/etc/nginx/sites-enabled/'):
            sudo('ln -sf ../sites-available/beau-dimanche.com')


def git_pull():

    # Push everything first. This is not strictly mandatory.
    # Don't fail if local user doesn't have my `pa` alias.
    local('git pa || true')

    with cd(env.root):
        if not is_local_environment():
            run('git checkout %s' % env.branch)
        run('git pull')


def activate_venv():

    return prefix('workon %s' % env.virtualenv)


@task
def restart_celery():
    """ Restart celery (only if detected as installed). """

    if exists('/etc/init.d/celeryd'):
        sudo("/etc/init.d/celeryd restart")


@task
def restart_supervisor():
    """ (Re-)upload configuration files and reload gunicorn via supervisor.

        This will reload only one service, even if supervisor handles more
        than one on the remote server. Thus it's safe for production to
        reload test :-)

    """

    if exists('/etc/supervisor'):

        # We need something more unique than project, in case we have
        # many environments on the same remote machine.
        program_name = '{0}_{1}'.format(env.project, env.environment)

        #
        # Upload an environment-specific supervisor configuration file.
        #

        superconf = os.path.join(env.root, 'config',
                                 'gunicorn_supervisor_{0}.conf'.format(
                                 env.environment))

        # os.path.exists(): we are looking for a LOCAL file!
        if not os.path.exists(superconf):
            superconf = os.path.join(os.path.dirname(__file__),
                                     'gunicorn_supervisor.template')

        destination = '/etc/supervisor/conf.d/{0}.conf'.format(program_name)

        context = {
            'root': env.root,
            'user': env.user,
            'branch': env.branch,
            'project': env.project,
            'program': program_name,
            'user_home': env.user_home,
            'virtualenv': env.virtualenv,
            'environment': env.environment,
        }

        upload_template(superconf, destination, context=context, use_sudo=True)

        #
        # Upload an environment-specific gunicorn configuration file.
        #

        uniconf = os.path.join(env.settings.BASE_ROOT, 'config',
                               'gunicorn_conf_{0}.py'.format(env.environment))

        # os.path.exists(): we are looking for a LOCAL file!
        if not os.path.exists(uniconf):
            unidefault = os.path.join(os.path.dirname(__file__),
                                      'gunicorn_conf_default.py')

            unidest = os.path.join(env.root, 'config',
                                   'gunicorn_conf_{0}.py'.format(
                                   env.environment))

            # copy the default configuration to remote::specific.
            put(unidefault, unidest)

        #
        # Reload supervisor, it will restart gunicorn.
        #

        # cf. http://stackoverflow.com/a/9310434/654755

        sudo("supervisorctl restart {0}".format(program_name))


@task
def requirements(upgrade=False):
    """ Install PIP requirements (and dev-requirements). """

    if upgrade:
        command = 'pip install -U'
    else:
        command = 'pip install'

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


@task
def collectstatic():
    """ Run the Django collectstatic management command. """

    with cd(env.root):
        with activate_venv():
            run('./manage.py collectstatic --noinput')


@task
def syncdb():
    """ Run the Django syndb management command. """

    with cd(env.root):
        with activate_venv():
            run('chmod 755 manage.py', quiet=True)
            run("./manage.py syncdb --noinput")


@task
def migrate(*args):
    """ Run the Django migrate management command. """

    with cd(env.root):
        with activate_venv():
            run("./manage.py migrate " + ' '.join(args))


@task
@with_remote_configuration
def createdb(remote_configuration=None, db=None, user=None, password=None,
             installation=False):
    """ Create the PostgreSQL user & database if they don't already exist.
        Install PostgreSQL on the remote system if asked to. """

    if installation:
        from .. import fabfile
        fabfile.db_postgresql()

    db, user, password = pg.temper_db_args(db, user, password)

    with settings(sudo_user=pg.get_admin_user()):
        if sudo(pg.SELECT_USER.format(user=user)).strip() == '':
            sudo(pg.CREATE_USER.format(user=user, password=password))

        sudo(pg.ALTER_USER.format(user=user, password=password))

        if sudo(pg.SELECT_DB.format(db=db)).strip() == '':
            sudo(pg.CREATE_DB.format(db=db, user=user))


@task(aliases=('initial', ))
def runable(fast=False, upgrade=False):
    """ Ensure we can run the {web,dev}server: db+req+sync+migrate+static. """

    if not fast:
        requirements(upgrade=upgrade)
        createdb()
        syncdb()
        migrate()

    collectstatic()


@task(aliases=('fast'))
def fastdeploy():
    """ Deploy FAST! For templates / static changes only. """

    deploy(fast=True)


@task
def deploy(fast=False):
    """ Pull code, ensure runable, restart services. """

    git_pull()
    runable(fast=fast, upgrade=not fast)

    if not fast:
        restart_celery()
        restart_supervisor()
