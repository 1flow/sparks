# -*- coding: utf-8 -*-
"""
    Fabric common rules for a Django project.


"""

import os
import logging

try:
    from fabric.api              import env, run, sudo, task, local
    #from fabric.operations       import put
    from fabric.contrib.files    import exists
    from fabric.context_managers import cd, prefix, settings

except ImportError:
    print('>>> FABRIC IS NOT INSTALLED !!!')
    raise

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


def install_base():
    """

    brew install redis
    ln -sfv /usr/local/opt/redis/*.plist ~/Library/LaunchAgents
    launchctl load ~/Library/LaunchAgents/homebrew.mxcl.redis.plist

    brew install memcached libmemcached
    ln -sfv /usr/local/opt/memcached/*.plist ~/Library/LaunchAgents
    launchctl load ~/Library/LaunchAgents/homebrew.mxcl.memcached.plist

    """

    print('install_base UNTESTED, refusing to run.')
    return

    sudo('apt-get install python-pip supervisor nginx-full')
    sudo('apt-get install postgresql redis-server memcached')
    sudo('apt-get install postgresql-server-dev-9.1 libmemcached-dev')
    sudo('apt-get install build-essential python-all-dev')
    sudo('pip install virtualenv virtualenvwrapper')

    if not exists('/etc/nginx/sites-available/beau-dimanche.com'):
        #put('config/nginx-site.conf', '')
        pass

    if not exists('/etc/nginx/sites-enabled/beau-dimanche.com'):
        with cd('/etc/nginx/sites-enabled/'):
            sudo('ln -sf ../sites-available/beau-dimanche.com')


def is_local_environment():
    is_local = env.environment == 'local' or (
        env.environment == 'test'
            and env.host_string == 'localhost')

    return is_local


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

    if exists('/etc/init.d/celeryd'):
        sudo("/etc/init.d/celeryd restart")


@task
def restart_gunicorn():

    if exists('/etc/init.d/gunicorn'):
        run("sudo /etc/init.d/gunicorn restart")


@task
def restart_supervisor():

    if exists('/etc/init.d/supervisord'):
        run("sudo /etc/init.d/supervisord restart")


@task
def requirements():
    with cd(env.root):
        with activate_venv():

            if is_local_environment():
                dev_req = os.path.join(env.root, env.dev_requirements_file)

                if not exists(dev_req):
                    dev_req = os.path.join(os.path.dirname(__file__),
                                           'dev-requirements.txt')

                run("pip install -U --requirement {requirements_file}".format(
                    requirements_file=dev_req))

            req = os.path.join(env.root, env.requirements_file)
            LOGGER.info(req)

            if not exists(req):
                req = os.path.join(os.path.dirname(__file__),
                                   'requirements.txt')

            run("pip install -U --requirement {requirements_file}".format(
                requirements_file=req))


@task
def collectstatic():
    with cd(env.root):
        with activate_venv():
            run('./manage.py collectstatic --noinput')


@task
def syncdb():
    with cd(env.root):
        with activate_venv():
            run('chmod 755 manage.py', quiet=True)
            run("./manage.py syncdb --noinput")


@task
def migrate(*args):
    with cd(env.root):
        with activate_venv():
            run("./manage.py migrate " + ' '.join(args))


@task
def createdb():
    """ Create the PostgreSQL database. Should do OK if already existing.

    OSX Installation notes:

    brew install postgresql
    initdb /usr/local/var/postgres -E utf8
    ln -sfv /usr/local/opt/postgresql/*.plist ~/Library/LaunchAgents
    launchctl load ~/Library/LaunchAgents/homebrew.mxcl.postgresql.plist
    psql template1

    """

    db       = env.settings.DATABASES['default']['NAME']
    user     = env.settings.DATABASES['default']['USER']
    password = env.settings.DATABASES['default']['PASSWORD']

    base_cmd    = 'psql template1 -tc "{0}"'
    select_user = base_cmd.format("SELECT usename from pg_user "
                                  "WHERE usename = '%s';" % user)
    create_user = base_cmd.format("CREATE USER %s WITH PASSWORD '%s';"
                                  % (user, password))
    alter_user  = base_cmd.format("ALTER USER %s WITH ENCRYPTED "
                                  "PASSWORD '%s';" % (user, password))
    select_db   = base_cmd.format("SELECT datname FROM pg_database "
                                  "WHERE datname = '%s';" % db)
    create_db   = base_cmd.format("CREATE DATABASE %s OWNER %s;"
                                  % (db, user))

    if is_local_environment():
        if run(select_user, quiet=True).strip() == '':
            run(create_user)

        run(alter_user)

        if run(select_db, quiet=True).strip() == '':
            run(create_db)

    else:
        with settings(sudo_user="postgres"):
            if sudo(select_user, quiet=True).strip() == '':
                sudo(create_user)

            sudo(alter_user)

            if sudo(select_db, quiet=True).strip() == '':
                sudo(create_db)


@task(aliases=('initial', ))
def runable():

    createdb()
    requirements()
    syncdb()
    migrate()
    collectstatic()


@task
def deploy():
    git_pull()
    runable()
    restart_gunicorn()
    restart_supervisor()
