# -*- coding: utf-8 -*-
""" Sparks Django utils. """

# import uuid
import time
import logging

from collections import namedtuple

from django.http import HttpResponse
from django.conf import settings

from rest_framework import serializers


LOGGER = logging.getLogger(__name__)


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


def NamedTupleChoices(name, *choices):
    """Factory function for quickly making a namedtuple.

    This namedtuple is suitable for use in a Django model as a choices
    attribute on a field. It will preserve order.

    Usage::

        class MyModel(models.Model):
            COLORS = NamedTupleChoices('COLORS',
                ('BLACK', 0, _(u'Black')),
                ('WHITE', 1, _(u'White')),
            )
            colors = models.PositiveIntegerField(choices=COLORS.get_choices())

        >>> MyModel.COLORS.BLACK
        0
        >>> MyModel.COLORS.get_choices()
        [(0, 'Black'), (1, 'White')]

        class OtherModel(models.Model):
            GRADES = NamedTupleChoices('GRADES',
                ('FR', 'FR', _(u'Freshman')),
                ('SR', 'SR', _(u'Senior')),
            )
            grade = models.CharField(max_length=2, choices=GRADES.get_choices())

        >>> OtherModel.GRADES.FR
        'FR'
        >>> OtherModel.GRADES.get_choices()
        [('FR', 'Freshman'), ('SR', 'Senior')]

    Inspired from https://djangosnippets.org/snippets/2402/
    The Django snipplet has been cleaned up and used differently
    (names come first, I prefer).
    """

    class Choices(namedtuple(name,
                  tuple(aname for aname, value, descr in choices))):

        __slots__ = ()
        _reverse = dict((value, aname) for aname, value, descr in choices)
        _revsymb = dict((value, descr) for aname, value, descr in choices)
        _choices = tuple(descr for aname, value, descr in choices)

        def get_choices(self):
            return zip(tuple(self), self._choices)

        def symbolic(self, index):
            return self._reverse[index]

        def get(self, index):
            try:
                return self._choices[index]
            except:
                return self._revsymb[index]

    return Choices._make(tuple(value for aname, value, descr in choices))


class WithoutNoneFieldsSerializer(serializers.ModelSerializer):

    """ Exclude model fields which are ``None``.

    This eventually includes foreign keys and other special fields.

    Source: https://gist.github.com/Karmak23/5a40beb1e18da7a61cfc
    """

    def to_native(self, obj):
        """ Remove all ``None`` fields from serialized JSON.

        .. todo:: the action test is probably superfluous.
        """

        try:
            action = self.context.get('view').action

        except:
            # cf. http://dev.1flow.net/codega-studio/popshake/group/44727/
            # Happens for example when overriding the retreive method, where
            # view/action is missing from the context.
            action = None

        removed_fields = {}

        if action in (None, 'list', 'retrieve', 'create', 'update', ):
            if obj is not None:
                fields = self.fields.copy()

                for field_name, field_value in fields.items():
                    if isinstance(field_value,
                                  serializers.SerializerMethodField):

                        if getattr(self, field_value.method_name)(obj) is None:
                            removed_fields[field_name] = \
                                self.fields.pop(field_name)

                    else:
                        try:
                            if getattr(obj, field_name) is None:
                                removed_fields[field_name] = \
                                    self.fields.pop(field_name)
                        except:
                            LOGGER.exception(u'Could not getattr %s on %s',
                                             field_name, obj)

        # Serialize with the None fields removed.
        result = super(WithoutNoneFieldsSerializer, self).to_native(obj)

        # Restore removed fields in case we are serializing a QS
        # and other instances have the field non-None.
        self.fields.update(removed_fields)

        return result


def wait_for_redis(host=None, port=None, timeout=None, loopdelay=None):
    """ Wait for Redis to be ready before continuing.

    :param host: defaults to ``127.0.0.1``.
    :type host: str or unicode.
    :param port: defaults to 6379 if not given.
    :type port: int
    :param timeout: defaults to ``None`` (wait indefinitely).
    :type timeout: int
    :param loopdelay: time to wait between each poll. Defaults to ``0.1``.
    :type loopdelay: float

    Freely inspired from https://github.com/Stupeflix/waitredis/
    """

    # We import here to avoid depending on it directly in sparks.
    # Projects calling this function will already depend on it.
    import redis

    if host is None:
        host = '127.0.0.1'

    if port is None:
        port = 6379

    if loopdelay is None:
        loopdelay = 0.1

    client = redis.StrictRedis(host=host, port=port)
    start_time = time.time()

    while (timeout is None or time.time() - start_time < timeout):
        try:
            client.dbsize()

        except redis.ResponseError as exc:
            if exc.args[0].startswith('LOADING'):
                time.sleep(loopdelay)
            else:
                raise
        else:
            break
