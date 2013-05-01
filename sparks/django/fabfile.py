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
env.branch                = '<GIT-FLOW-DEPENDANT>'
env.use_ssh_config        = True


@task(aliases=('base', 'base_components'))
@with_remote_configuration
def install_components(remote_configuration=None):
    """ Install necessary packages to run a full Django stack.
        .. todo:: split me into packages/modules where appropriate. """

    # TODO: use the installation tasks
    # if installation:
    #     from ... import fabfile
    #     fabfile.db_postgresql()

    # OSX == test environment == no nginx/supervisor/etc
    if remote_configuration.is_osx:
        brew.brew_add(('redis', 'memcached', 'libmemcached', ))

        run('ln -sfv /usr/local/opt/redis/*.plist ~/Library/LaunchAgents')
        run('launchctl load ~/Library/LaunchAgents/homebrew.*.redis.plist')

        run('ln -sfv /usr/local/opt/memcached/*.plist ~/Library/LaunchAgents')
        run('launchctl load ~/Library/LaunchAgents/homebrew.*.memcached.plist')

        print('NO WEB-SERVER installed, assuming this is a dev machine.')

    else:
        apt.apt_add(('python-pip', 'supervisor', 'nginx-full',))
        apt.apt_add(('redis-server', 'memcached', 'libmemcached-dev', ))
        apt.apt_add(('build-essential', 'python-all-dev', ))

    # This is common to dev/production machines.
    pip.pip2_add(('virtualenv', 'virtualenvwrapper', ))


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

    from ... import fabfile
    fabfile.dev()
    fabfile.dev_postgresql()

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


@task(alias='gunicorn')
def restart_gunicorn_supervisor(fast=False):
    """ (Re-)upload configuration files and reload gunicorn via supervisor.

        This will reload only one service, even if supervisor handles more
        than one on the remote server. Thus it's safe for production to
        reload test :-)

    """

    if exists('/etc/supervisor'):

        # We need something more unique than project, in case we have
        # many environments on the same remote machine.
        program_name = '{0}_{1}'.format(env.project, env.environment)

        if not fast:

            #
            # Upload an environment-specific supervisor configuration file.
            #

            need_service_add = False
            superconf = os.path.join(env.root, 'config',
                                     'gunicorn_supervisor_{0}.conf'.format(
                                     env.environment))

            # os.path.exists(): we are looking for a LOCAL file!
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
                'user_home': env.user_home,
                'virtualenv': env.virtualenv,
                'environment': env.environment_vars,
            }

            if not exists(destination):
                need_service_add = True

            upload_template(superconf, destination, context=context,
                            use_sudo=True)

            #
            # Upload an environment-specific gunicorn configuration file.
            #

            uniconf = os.path.join(env.settings.BASE_ROOT, 'config',
                                   'gunicorn_conf_{0}.py'.format(
                                   env.environment))

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

        if need_service_add:
            sudo("supervisorctl add {0} && supervisorctl start {0}".format(
                 program_name))

            # No need.
            #sudo("supervisorctl reload")

        else:
            sudo("supervisorctl restart {0}".format(program_name))


# ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Django specific

@task(alias='static')
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
        from ... import fabfile
        fabfile.db_postgresql()

    db, user, password = pg.temper_db_args(db, user, password)

    with settings(sudo_user=pg.get_admin_user()):
        if sudo(pg.SELECT_USER.format(user=user)).strip() == '':
            sudo(pg.CREATE_USER.format(user=user, password=password))

        sudo(pg.ALTER_USER.format(user=user, password=password))

        if sudo(pg.SELECT_DB.format(db=db)).strip() == '':
            sudo(pg.CREATE_DB.format(db=db, user=user))


# ••••••••••••••••••••••••••••••••••••••••••••••••••••••• Deployment meta-tasks


@task(alias='restart')
def restart_services(fast=False):
    restart_nginx(fast=fast)
    restart_celery_service(fast=fast)
    restart_gunicorn_supervisor(fast=fast)


@task(aliases=('initial', ))
def runable(fast=False, upgrade=False):
    """ Ensure we can run the {web,dev}server: db+req+sync+migrate+static. """

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

    init_environment()

    runable(fast=fast, upgrade=upgrade)

    restart_services(fast=fast)
