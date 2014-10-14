# -*- coding: utf-8 -*-
""" Django sparks. """

from django.http import HttpResponse
from django.utils import simplejson

try:
    # Django 1.7 has it: http://stackoverflow.com/a/2428192/654755
    from django.http import JsonResponse

except ImportError:

    class JsonResponse(HttpResponse):

        """ a JSON response. """

        def __init__(self, content, mimetype='application/json',
                     status=None, content_type=None):
            """ Json response init. """

            super(JsonResponse, self).__init__(
                content=simplejson.dumps(content),
                mimetype=mimetype,
                status=status,
                content_type=content_type,
            )
