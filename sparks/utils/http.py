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

import re
import logging
import charade

from collections import namedtuple
from bs4 import BeautifulSoup

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


def detect_encoding_from_requests_response(response, meta=False, deep=False):
    """ Try to detect encoding as much as possible.

    :param:`response` beiing a :module:`requests` response, this function
    will try to detect the encoding as much as possible. Fist, the "normal"
    response encoding will be tried, else the headers will be parsed, and
    finally the ``<head>`` of the ``<html>`` content will be parsed. If
    nothing succeeds, we will rely on :module:`charade` to guess from the
    content.

    .. todo:: we have to check if content-type is HTML before parsing the
        headers. For now you should use this function only on responses
        which you are sure they will contain HTML.
    """

    if getattr(response, 'encoding', None) and not (meta or deep):

        # To understand, please read
        # http://docs.python-requests.org/en/latest/user/advanced/#encodings
        if response.encoding.lower() != 'iso-8859-1':
            if __debug__:
                LOGGER.debug(u'detect_encoding_from_requests_response(): '
                             u'detected %s via `requests` module.',
                             response.encoding)

            return response.encoding

    # If requests doesn't bring us any encoding or returns 'iso-8859-1',
    # we have 3 fallback options:
    # - inspect the server headers ourselves. This is fast, but rarely
    #   they exist (that's probably why requests failed), and sometimes
    #   they disagree with META tags,
    # - look up the META tags. This is fast too, but sometimes the tag
    #   is not present or the value is wrong too,
    # - detect it via `charade`. Quite slower, but gives accurate results.

    content_type = response.headers.get('content-type', None)

    # If found and no deeper search is wanted, return it.
    if content_type is not None and 'charset' in content_type \
            and not (meta or deep):

        encoding = content_type.lower().split('charset=')[-1]

        if __debug__:
            LOGGER.debug(u'detect_encoding_from_requests_response(): '
                         u'detected %s via server headers.',
                         encoding)

        return encoding

    # HTTP headers don't contain any encoding.
    # Search in page head, then try to detect from data.

    html_content = BeautifulSoup(response.content, 'lxml')

    found = False
    for meta_header in html_content.head.findAll('meta'):
        for attribute, value in meta_header.attrs.items():
            if attribute.lower() == 'http-equiv':
                if value.lower() == 'content-type':
                    # OMG o_O took time to find this one :
                    # In [73]: meta_header
                    # Out[73]: <meta content="text/html; charset=utf-8" …
                    # In [74]: meta_header.get('content')
                    # Out[74]: u'text/html; charset=iso-8859-1'
                    #
                    # We cannot rely on get('content') and need to
                    # fallback to good ol' RE searching. Thanks BS4.
                    content = unicode(meta_header).lower()
                    if 'charset' in content:
                        encoding = re.search('charset=([\w-]*)',
                                             content, re.I | re.U).group(1)
                        found = True
                        break
        if found:
            break

    # If no deeper search is wanted, return it now.
    if found and encoding not in ('text/html', '', None) and not deep:

        if __debug__:
            LOGGER.debug(u'detect_encoding_from_requests_response(): '
                         u'detected %s via HTML meta tags.',
                         encoding)

        return encoding

    try:
        charade_result = charade.detect(response.content)

    except:
        pass

    else:
        if __debug__:
            LOGGER.debug(u'detect_encoding_from_requests_response(): '
                         u'detected %s via `charade` module (with %s%% '
                         u'confidence).',
                         charade_result['encoding'],
                         charade_result['confidence'])
        return charade_result['encoding']

    LOGGER.critical('detect_encoding_from_requests_response(): could not '
                    u'detect encoding of %s via all test methods.', response)
    return None
