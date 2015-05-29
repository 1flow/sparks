# -*- coding: utf-8 -*-
""" Sparks Django middlewares. """

from threading import local

_user = local()


class CurrentUserMiddleware(object):

    """ Store current user locally for each request.

    Usage:

    - in settings:

         MIDDLEWARE_CLASSES = (
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.common.CommonMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',

            …

            'sparks.django.middleware.CurrentUserMiddleware',

            …
        )

    - in models:

        class CreatorAbstractModel(models.Model):

            ''' Common Abstract base to many models. '''

            user = models.ForeignKey('User', null=True, blank=True,
                                     verbose_name=_(u'creator'),
                                     default=get_current_user)

            class Meta:
                abstract = True

    """

    def process_request(self, request):
        """ Store request user. """
        _user.value = request.user


def get_current_user():
    """ Return current thread user, or None. """

    try:
        return _user.value

    except:
        return None
