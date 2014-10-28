# -*- coding: utf-8 -*-
""" Django sparks. """

import json

try:
    from user_agents import parse as user_agents_parse

except ImportError:
    user_agents_parse = None

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
                     status=None, content_type=None, **kwargs):
            """ Json response init. """

            indent = kwargs.get('indent', None)

            if json_util:
                content = json.dumps(content, indent=indent,
                                     default=json_util.default)

            else:
                content = json.dumps(content, indent=indent)

            super(JsonResponse, self).__init__(
                content=content,
                mimetype=mimetype,
                status=status,
                content_type=content_type,
            )


def human_user_agent(request):
    """ Return True if we think we have a human browsing.

    The function takes a Django ``request`` as parameter, and will inspect
    the ``HTTP_USER_AGENT`` meta header.

    .. note:: obviously, if the remote program is faking a real browser user
        agent, this function will not do any miracle and will guess it as
        a human, whereas it is not.
    """

    if user_agents_parse is None:
        raise RuntimeError(u'Python module “user-agents” does not '
                           u'seem to be installed')

    user_agent_string = request.META.get('HTTP_USER_AGENT', '')

    user_agent = user_agents_parse(user_agent_string)

    if user_agent.is_bot:
        return False

    if user_agent.is_mobile or user_agent.is_tablet:
        return True

    if user_agent.is_pc:
        if user_agent.is_touch_capable:
            return True

        if user_agent.browser.family in ('Firefox', 'Chrome', ):
            return True

    #
    # TODO: finish this…
    #

    return False
