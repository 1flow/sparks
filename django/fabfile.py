# -*- coding: utf-8 -*-
"""
    Fabric common rules for a Django project.


"""
try:
    from fabric.api              import env, run, sudo, task
    #from fabric.operations       import put
    from fabric.contrib.files    import exists
    from fabric.context_managers import cd, prefix
except ImportError:
    print('>>> FABRIC IS NOT INSTALLED !!!')
    raise


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
    sudo('pip install virtualenv virtualenvwrapper')

    if not exists('/etc/nginx/sites-available/beau-dimanche.com'):
        #put('config/nginx-site.conf', '')
        pass

    if not exists('/etc/nginx/sites-enabled/beau-dimanche.com'):
        with cd('/etc/nginx/sites-enabled/'):
            sudo('ln -sf ../sites-available/beau-dimanche.com')


def git_pull():
    with cd(env.root):
        run('git pull')


def activate_venv():

    return prefix('workon %s' % env.virtualenv)


@task
def restart_celery():

    sudo("/etc/init.d/celeryd restart")


@task
def restart_gunicorn():

    run("sudo /etc/init.d/gunicorn restart")


@task
def restart_supervisor():

    run("sudo /etc/init.d/supervisord restart")


@task
def requirements():
    with activate_venv():
        run("pip install --requirement {requirements_file}".format(**env))


@task
def collectstatic():
    with cd(env.root):
        with activate_venv():
            run('./manage.py collectstatic --noinput')


@task
def syncdb():
    with cd(env.code_root):
        with activate_venv():
            run("./manage.py syncdb --noinput")


@task
def migrate(*args):
    with cd(env.root):
        with activate_venv():
            run("./manage.py migrate " + ' '.join(args))


@task(aliases=('runable', ))
def initial():
    requirements()
    syncdb()
    migrate()
    collectstatic()


@task
def deploy():
    git_pull()
    requirements()
    syncdb()
    migrate()
    collectstatic()
    restart_gunicorn()
    restart_supervisor()
