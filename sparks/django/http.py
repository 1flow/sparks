# -*- coding: utf-8 -*-
""" Django sparks. """

import json

try:
    from bson import json_util

except ImportError:
    json_util = None

from django.http import HttpResponse

try:
    # Django 1.7 has it: http://stackoverflow.com/a/2428192/654755
    from django.http import JsonResponse

except ImportError:

    class JsonResponse(HttpResponse):

        """ a JSON response. """

        def __init__(self, content, mimetype='application/json',
                     status=None, content_type=None):
            """ Json response init. """

            if json_util:
                content = json.dumps(content, default=json_util.default)

            else:
                content = json.dumps(content)

            super(JsonResponse, self).__init__(
                content=content,
                mimetype=mimetype,
                status=status,
                content_type=content_type,
            )
