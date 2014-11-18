# -*- coding: utf-8 -*-
"""
Sparks helpers, functions and classes for the Django admin.

.. note:: this module will need to import django settings.
    Make sure it is available and set before importing.

.. versionadded:: 1.17
"""

from django.contrib import admin

from django.utils.translation import ugettext_lazy as _


class NullListFilter(admin.SimpleListFilter):

    """ A simple list filter that acts on nullable fields.

        class StartNullListFilter(NullListFilter):
            title = u'Started'
            parameter_name = u'started'

    and finally:

        class SomeModelAdmin(admin.ModelAdmin):
            list_filter = (StartNullListFilter, )


    Source: http://stackoverflow.com/q/7691890/654755
    """

    def lookups(self, request, model_admin):
        """ Return the lookups. """

        return (
            ('1', _(u'Null'), ),
            ('0', _(u'Not null'), ),
        )

    def queryset(self, request, queryset):
        """ Filter the QS. """

        if self.value() in ('0', '1'):
            kwargs = {'{0}__isnull'.format(self.parameter_name):
                      self.value() == '1'}

            return queryset.filter(**kwargs)

        return queryset


def null_filter(field, title_=None):
    """ Use the NullListFilter class without cluttering admin.py.

    Using this class maker avoids creating too much 2-lines classes.
    """

    class NullListFieldFilter(NullListFilter):
        parameter_name = field
        title = title_ or parameter_name

    return NullListFieldFilter
