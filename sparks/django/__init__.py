# -*- coding: utf-8 -*-
""" Django sparks. """

import sys
import logging

LOGGER = logging.getLogger(__name__)


def create_admin_user(username=None, email=None, password=None):
    """ Create an admin user, and don't crash if there is one already. """

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

            except IntegrityError as e:
                try:
                    if User.objects.get(username=admin_username,
                                        is_superuser=True):
                        pass

                    else:
                        admin = User.objects.get(username=admin_username)
                        admin.is_superuser = True
                        admin.save()

                        LOGGER.warning('Admin user was not super user!')

                except:
                    LOGGER.exception(u'Could not check existing admin user'
                                     u'while trying to deal with an '
                                     u'IntegrityError')
                    raise e

            except:
                LOGGER.warning('Sparks could not create an admin user!')

            else:
                LOGGER.info('Created superuser %s.', user)
