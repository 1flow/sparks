# -*- coding: utf-8 -*-
"""
    A global and environment/host-dependant settings system for Django.

"""

import os
import logging
from os.path import dirname, abspath, join, exists
from ..fabric import local_configuration as platform

LOGGER = logging.getLogger(__name__)


def find_settings(settings__file__name):
    """ Returns the first existing settings file, out of:

        - the one specified in the environment
          variable :env:`SPARKS_DJANGO_SETTINGS`,
        - one constructed from either the full hostname,
          then the host shortname (without TLD), then only
          the domain name. If the current hostname is short
          from the start (eg. :file:`/etc/hostname` contains
          a short name only), obviously only one will be tried.
        - a :file:`default` configuration eg.
          a :file:`settings/default.py` file.

        If none of these files are to be found, a :class:`RuntimeError`
        will be raised.

        These files will be looked up in the same directy as the caller.
        To acheive this, use them like this:

            project/
                settings/
                    __init__.py
                    myhostname-domain-ext.py
                    otherhost-domain-ext.py
                    special-config.py

        In the file :file:`__init__.py`: just write:

            from sparks.django.settings import find_settings()
            execfile(find_settings(__file__))

        The :file:`myhostname-domain-ext.py` and others are completely
        standard settings file. You are free to use them as you like, eg.
        plain Django settings files, or combined in any way that pleases
        you. You could for example create a :file:`common.py`, import it
        in all other, and override only a part of its attributes in them.

        .. note:: if you hostname starts with a digit, this **first** (and
            only the first) digit will be replaced by this name in letters.
            Eg. ``1flow.net`` will be looked up as ``oneflow-net.py``, and
            ``21jump.street.com`` will be looked up as
            ``two1jump-street-com.py``.

    """

    digits = {
        '0': 'zero',
        '1': 'one',
        '2': 'two',
        '3': 'three',
        '4': 'four',
        '5': 'five',
        '6': 'six',
        '7': 'seven',
        '8': 'eight',
        '9': 'nine',
    }

    here = dirname(abspath(settings__file__name))

    def settings_path(settings_name):

        if settings_name[0].isdigit():
            # '1flow' becomes 'oneflow'
            settings_name = digits[settings_name[0]] + settings_name[1:]

        return join(here, settings_name + '.py')

    candidates = []

    environ_settings = os.environ.get('SPARKS_DJANGO_SETTINGS', None)

    if environ_settings:
        candidates.append(settings_path(environ_settings))
        LOGGER.info(u'Picked up environment variable '
                    u'SPARKS_DJANGO_SETTINGS="{0}".'.format(
                    environ_settings))

    fullnodename = platform.hostname.replace('.', '-')
    candidates.append(settings_path(fullnodename))

    try:
        shortname, domainname = platform.hostname.split('.', 1)

    except ValueError:
        # The hostname is a short one, without the domain.
        pass

    else:
        candidates.extend(settings_path(x.replace('.', '-'))
                          for x in (shortname, domainname))

    candidates.append(settings_path('default'))

    for candidate in candidates:
        if exists(candidate):
            LOGGER.debug(u'Using first found settings file "{0}"'.format(
                         candidate))
            return candidate

    raise RuntimeError(u'No settings found! Tried {0}'.format(', '.join(
                       candidates)))
