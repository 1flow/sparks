# -*- coding: utf-8 -*-
"""
Copyright 2012-2014 Olivier Cortès <oc@1flow.io>.

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


from django.template import Library, TemplateSyntaxError
from django.utils.translation import ugettext_lazy as _

from sparks.foundations import utils as sfu

register = Library()


@register.inclusion_tag('snippets/countdown.html')
def countdown(value, redirect=None, limit=0, show_seconds=True,
              format=None, spacer=None):
    """ Create a JS countdown.

    From http://www.plus2net.com/javascript_tutorial/countdown.php
    """

    if redirect is None:
        redirect = '/'

    if limit > 0:
        operation    = '+'
        round_value  = 0
        counter_test = '<='

    else:
        operation    = '-'
        round_value  = 0        # WAS: 2
        counter_test = '>='

    if format is None or format == 'long':
        separator = ', '
        short     = False
        units     = {
            'day': _('day'),
            'days': _('days'),
            'hour': _('hour'),
            'hours': _('hours'),
            'minute': _('minute'),
            'minutes': _('minutes'),
            'second': _('second'),
            'seconds': _('seconds'),
        }

    elif format == 'abbr':
        separator = ' '
        short     = True
        units     = {
            'day': _('day'),
            'days': _('days'),
            'hour': _('hour'),
            'hours': _('hours'),
            'minute': _('min'),
            'minutes': _('mins'),
            'second': _('sec'),
            'seconds': _('secs'),
        }
    elif format == 'short':
        separator = ' '
        short     = True
        units     = {
            'day': _('d'),
            'days': _('d'),
            'hour': _('h'),
            'hours': _('h'),
            'minute': _('m'),
            'minutes': _('m'),
            'second': _('s'),
            'seconds': _('s'),
        }
    else:
        raise TemplateSyntaxError("'countdown' 'format' keyword argument "
                                  "must be either 'short', 'abbr' or 'long'")

    return {
        'name': sfu.unique_hash(only_letters=True),
        'units': units,
        'short': short,
        'value': value,
        'limit': limit,
        'unit_sep': ' ' if spacer is None else spacer,
        'redirect': redirect,
        'operation': operation,
        'separator': separator,
        'round_value': round_value,
        'show_seconds': show_seconds,
        'counter_test': counter_test,
    }
