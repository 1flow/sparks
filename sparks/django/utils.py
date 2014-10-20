# -*- coding: utf-8 -*-
""" Sparks Django utils. """

from collections import namedtuple

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


def NamedTupleChoices(name, choices_tuple):
    """Factory function for quickly making a namedtuple.

    This namedtuple is suitable for use in a Django model as a choices
    attribute on a field. It will preserve order.

    Usage::

        class MyModel(models.Model):
            COLORS = NamedTupleChoices('COLORS', (
                ('BLACK', 0, _(u'Black')),
                ('WHITE', 1, _(u'White')),
            ))
            colors = models.PositiveIntegerField(choices=COLORS)

        >>> MyModel.COLORS.BLACK
        0
        >>> MyModel.COLORS.get_choices()
        [(0, 'Black'), (1, 'White')]

        class OtherModel(models.Model):
            GRADES = NamedTupleChoices('GRADES', (
                ('FR', 'FR', _(u'Freshman')),
                ('SR', 'SR', _(u'Senior')),
            ))
            grade = models.CharField(max_length=2, choices=GRADES)

        >>> OtherModel.GRADES.FR
        'FR'
        >>> OtherModel.GRADES.get_choices()
        [('FR', 'Freshman'), ('SR', 'Senior')]

    Inspired from https://djangosnippets.org/snippets/2402/
    The Django snipplet has been cleaned up and used differently
    (names come first, I prefer).
    """

    class Choices(namedtuple(name,
                  tuple(aname for aname, value, descr in choices_tuple))):

        __slots__ = ()
        _choices = tuple(descr for aname, value, descr in choices_tuple)

        def get_choices(self):
            return zip(tuple(self), self._choices)

    return Choices._make(tuple(value for aname, value, descr in choices_tuple))
