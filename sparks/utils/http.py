# -*- coding: utf-8 -*-
u"""
Copyright 2012-2015 Olivier Cortès <oc@1flow.io>.

This file is part of the sparks project.

sparks is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of
the License, or (at your option) any later version.

sparks is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with sparks.  If not, see http://www.gnu.org/licenses/

"""

import logging

from collections import namedtuple

url_tuple = namedtuple('url', ['scheme', 'host_and_port', 'remaining', ])
url_port_tuple = namedtuple('url_port',
                            ['scheme', 'hostname', 'port', 'remaining', ])


LOGGER = logging.getLogger(__name__)


class SplitUrlException(Exception):

    """ Raised when an URL is reaaaaally bad. """

    pass


def split_url(url, split_port=False):
    u""" Split an URL into a named tuple for easy manipulations.

    Eg. “http://test.com/toto becomes:
    ('scheme'='http', 'host_and_port'='test.com', 'remaining'='toto').

    if :param:`split_port` is ``True``, the returned namedtuple is of the form:

    ('scheme'='http', 'hostname'='test.com', 'port'=80, 'remaining'='toto').

    In this case, ``port`` will be an integer. All other attributes are strings.

    In case of an error, it will raise a :class:`SplitUrlException` exception.
    """

    try:
        proto, remaining = url.split('://', 1)

    except:
        raise SplitUrlException(u'Unparsable url “{0}”'.format(url))

    try:
        host_and_port, remaining = remaining.split('/', 1)

    except ValueError:
        host_and_port = remaining
        remaining     = u''

    if split_port:
        try:
            hostname, port = host_and_port.split(':')

        except ValueError:
            hostname = host_and_port
            port = '80' if proto == 'http' else '443'

        return url_port_tuple(proto, hostname, int(port), remaining)

    return url_tuple(proto, host_and_port, remaining)
