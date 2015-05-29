# -*- coding: utf-8 -*-
""" Sparks Django middlewares. """

from threading import local

_user = local()


class CurrentUserMiddleware(object):

    """ Store current user locally for each request. """

    def process_request(self, request):
        """ Store request user. """
        _user.value = request.user


def get_current_user():
    """ Return current thread user, or None. """

    try:
        return _user.value

    except:
        return None
