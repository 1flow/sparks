# -*- coding: utf-8 -*-

from django.http import HttpResponse


class HttpResponseTemporaryServerError(HttpResponse):
    """ A custom 503 Error, to avoid bare 500. Search engines seem to like
        503 more; 500 is seen as a sign of poor quality. """

    status_code = 503

    def __init__(self, *args, **kwargs):
        HttpResponse.__init__(self, *args, **kwargs)
        self['Retry-After'] = '3600'
