# -*- coding: utf-8 -*-
"""
    Django sparks.

"""

import sys
import logging

LOGGER = logging.getLogger(__name__)


def create_admin_user(username=None, email=None, password=None):

    # additional process for creating an admin without input or misc data…
    # cf. http://stackoverflow.com/a/13466241/654755
    for arg in sys.argv:
        if arg.lower() == 'syncdb':
            LOGGER.info('sparks syncdb post process…')
            from django.contrib.auth import get_user_model
            from django.conf import settings
            from django.db import IntegrityError

            admin_username = 'admin' if username is None else username
            admin_email    = email or 'contact@oliviercortes.com'
            admin_password = password or ('nimdatoor'
                                          if settings.DEBUG
                                          else '-change_me_now+')

            User = get_user_model()

            try:
                user = User.objects.create_superuser(username=admin_username,
                                                     email=admin_email,
                                                     password=admin_password)
                LOGGER.info('Created superuser %s.', user)

            except IntegrityError, e:
                # NOTE: do not use e.message:
                # DeprecationWarning: BaseException.message
                # has been deprecated as of Python 2.6
                if not 'duplicate key' in e.args[0]:
                    raise
            except:
                LOGGER.warning('Sparks could not create an admin user!')
