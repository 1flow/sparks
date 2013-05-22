# -*- coding: utf-8 -*-
"""
    Sparks helpers, functions and classes for the Django admin.

    .. note:: this module will need to import django settings.
        Make sure it is available and set before importing.

    .. versionadded:: 1.17
"""

from django.conf import settings


DEFAULT_TRUNCATE_LENGTH = 50

languages = settings.TRANSMETA_LANGUAGES \
        if hasattr(settings, 'TRANSMETA_LANGUAGES') \
        else settings.LANGUAGES


def truncate_field(cls, field_name, truncate_length=None):
    """ Returns a callable that will truncate the field content.

        Useful in the Django admin change list. to include long fields
        without them to eat up all the space or making the page too large.
    """

    if truncate_length is None:
        truncate_length = DEFAULT_TRUNCATE_LENGTH

    def wrapped(self, obj):
        value = getattr(obj, field_name)

        return value[:truncate_length] + (
            value[truncate_length:] and u'…')

    wrapped.admin_order_field = field_name
    wrapped.short_description = cls._meta.get_field_by_name(
        field_name)[0].verbose_name

    return wrapped
