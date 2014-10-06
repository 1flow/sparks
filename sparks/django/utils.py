# -*- coding: utf-8 -*-
""" Sparks Django utils. """

from django.http import HttpResponse
from django.conf import settings


DEFAULT_TRUNCATE_LENGTH = 50

languages = settings.TRANSMETA_LANGUAGES \
    if hasattr(settings, 'TRANSMETA_LANGUAGES') \
    else settings.LANGUAGES


class HttpResponseTemporaryServerError(HttpResponse):

    """ A custom 503 Error, to avoid bare 500.

    Search engines seem to like 503 more.
    500 is seen as a sign of poor quality.
    """

    status_code = 503

    def __init__(self, *args, **kwargs):
        """ A simple init, pep257. """
        HttpResponse.__init__(self, *args, **kwargs)
        self['Retry-After'] = '3600'


def truncate_field(cls, field_name, truncate_length=None):
    """ Return a callable that will truncate the field content.

    Useful in the Django admin change list. to include long fields
    without them to eat up all the space or making the page too large.
    """

    if truncate_length is None:
        truncate_length = DEFAULT_TRUNCATE_LENGTH

    def wrapped(self, obj):
        value = getattr(obj, field_name) or u'<NO_VALUE>'

        return value[:truncate_length] + (
            value[truncate_length:] and u'…')

    wrapped.admin_order_field = field_name
    wrapped.short_description = cls._meta.get_field_by_name(
        field_name)[0].verbose_name

    return wrapped
