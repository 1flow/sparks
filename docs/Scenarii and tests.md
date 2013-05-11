test sparks django:

# Simple

## Scenario 1

- local development
    - pg
    - django's runserver

- one remote server, which hosts:
    - test: ~user1/www-test
    - production: ~user1/www
    - user1 is sudo
        - sudo postgres for db
    - one PG with 2 databases
    - supervisor with 2 unicorn services

fab local runable
fab test deploy
fab production deploy
fab test fastdeploy
fab production fastdeploy


## Scenario 2

- local development
    - idem
- one remote server:
    - test ~user1/www
    - production ~user2/www
    - pg with 2 databases



# Complex

- sparks dynamic settings
- local development
    - idem
    - autodetect settings based on hostname
    - with mysubapp (=2 possible `runserver`)
        - same DB,
        - Django multisite / multi-settings
        - fixed settings with sparks env variable

- 1 remote PG server:
    - 2 databases (test / production)
- 1 remote redis server:
    - 2 databases (test / production)
- 2 remote servers:
    - test:
        - cache disabled
        - ~user1/www
        - 2 gunicorn services with each a different configuration
    - production:
        - cache enabled
        - idem test

fab local runable
fab test deploy
fab production deploy
fab test fastdeploy
fab production fastdeploy

fab local mysubapp runable
fab test mysubapp deploy
fab production mysubapp deploy
fab test mysubapp fastdeploy
fab production mysubapp fastdeploy


# Tests

@task
@with_remote_configuration
def test1(remote_configuration=None):
    from sparks import platform
    print str(getattr(platform, 'django_settings', None))
    print str(getattr(remote_configuration, 'django_settings', None))
