# -*- coding: utf-8 -*-
u"""
Copyright 2012-2014 Olivier Cortès <oc@1flow.io>.

This file is part of the 1flow project.

1flow is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of
the License, or (at your option) any later version.

1flow is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with 1flow.  If not, see http://www.gnu.org/licenses/

"""

import re
import humanize

from django.template import Node, TemplateSyntaxError
from django.utils.encoding import smart_text
from django.core.urlresolvers import reverse
from django.db.models.query import QuerySet

from sparks.django.templatetags import register
from sparks.django.utils import NamedTupleChoices


# ——————————————————————————————————————————————————————————————————— Internals


def get_view_name(context):
    """ Extract the current view name from context. """

    # context['request'].resolver_match.func
    # context['request'].resolver_match.args
    # context['request'].resolver_match.kwargs
    # context['request'].resolver_match.view_name

    try:
        return context['request'].resolver_match.view_name

    except AttributeError:
        # Happens on / when the request is a
        # WSGIRequest and not an HttpRequest.
        return u'home'


class CaptureasNode(Node):

    u""" Parsing node for “captureas” tag. """

    def __init__(self, nodelist, varname):
        """ Hello, pep257. Stop boring me with 2-lines __init__ methods. """

        self.nodelist = nodelist
        self.varname  = varname

    def render(self, context):
        """ Hello, pep257. Stop boring me with 2-lines methods. """

        output = self.nodelist.render(context)
        context[self.varname] = output
        return ''


class FirstOfAsNode(Node):

    u""" Parsing node for “firstofas” tag. """

    def __init__(self, args, variable_name=None):
        """ Hello, pep257. Stop boring me with 2-lines __init__ methods. """

        self.vars = args
        self.variable_name = variable_name

    def render(self, context):
        """ Resolve the first resolvable argument and store it in context. """

        for var in self.vars:
            value = var.resolve(context, True)

            if value:
                if self.variable_name:
                    context[self.variable_name] = value
                    break

                else:
                    return smart_text(value)

        return ''


# ———————————————————————————————————————————————————————————————————————— Tags


@register.tag(name='captureas')
def do_captureas(parser, token):
    """ Taken from http://djangosnippets.org/snippets/545/ verbatim.

    Initial source: https://code.djangoproject.com/ticket/7239
    """

    try:
        tag_name, args = token.contents.split(None, 1)

    except ValueError:
        raise TemplateSyntaxError(
            "'captureas' node requires a variable name.")

    nodelist = parser.parse(('endcaptureas',))
    parser.delete_first_token()

    return CaptureasNode(nodelist, args)


@register.tag
def firstofas(parser, token):
    """ Like Django's ``firstof``, but in a context variable.

    Original idea: https://code.djangoproject.com/ticket/12199
    """

    bits = token.split_contents()[1:]
    variable_name = None
    expecting_save_as = bits[-2] == 'as'

    if expecting_save_as:
        variable_name = bits.pop(-1)
        bits = bits[:-1]

    if len(bits) < 1:
        raise TemplateSyntaxError(
            "'firstofas' statement requires at least one argument")

    return FirstOfAsNode([parser.compile_filter(bit) for bit in bits],
                         variable_name)


# ————————————————————————————————————————————————————————————————— Simple tags


@register.simple_tag(takes_context=True)
def reverse_active(context, views_names, return_value=None):
    u""" Return an ``active`` string if the current view matches.

    This is used to mark some CSS classes ``active``. If nothing matches,
    return an empty string.

    :param view_names: a string containing view names,
        separated by commas without spaces.

    :param return_value: anything that will be returned instead of the
        string ``active`` if the current view matches.

    Usage, in the template:

        class="{% reverse_active "view_name" %}"
        class="{% reverse_active "view_name1,view_name2" "my-active" %}"

    Taken from http://gnuvince.wordpress.com/2007/09/14/a-django-template-tag-for-the-current-active-page/  # NOQA
    and extended a lot to simplify template calls…
    """

    for view_name in views_names.split(','):
        if reverse(view_name) == context['request'].path:
            return return_value or u'active'

    return u''


@register.simple_tag(takes_context=True)
def view_name_active(context, pattern, return_value=None):
    """ Same as reverse active, but for URLs without any view.

    :param:`pattern` must be a valid regular expression.

    Usage:
        class="{% active "/help/" "top-menu-element-active" %}"

    """

    view_name = get_view_name(context)

    if re.search(pattern, view_name):
        return return_value or u'active'

    return u''


@register.simple_tag(takes_context=True)
def reqpath_active(context, pattern, return_value=None):
    """ Same as reverse active, but for request.path.

    :param pattern: must be a valid regular expression.
    :param return_value: any string, "active" if none supplied.

    """

    reqpath = context['request'].get_full_path()

    if re.search(pattern, reqpath):
        return return_value or u'active'

    return u''


# ————————————————————————————————————————————————————————————————————— Filters


@register.filter(name='times')
def times(number):
    u""" Simply return a Python range 1 → :param:`number`. """

    return range(number)


@register.filter
def lookup(d, key, symbolic=None):
    """ Get a value from a dictionnary, given a key.

    Too bad Django doesn't have this one included.

    .. note:: at first try, this function will ``int()`` the key,
        because sometimes the value comes directly from the request
        and could still be a string. This could be though as bad by
        some people. Feel free to scream.
    """

    if isinstance(d, NamedTupleChoices):
        if bool(symbolic):
            return d.symbolic(key)

        return d.index(key)

    try:
        return d[int(key)]

    except KeyError:
        return d[key]


@register.filter(name='naturalsize')
def naturalsize(number, type=None):
    """ Return a humanized (and translated) file size. """

    with humanize.i18n.django_language():
        if type is None:
            return humanize.naturalsize(number)

        if type in ('bin', 'binary'):
            return humanize.naturalsize(number, binary=True)

        if type in ('gnu', 'GNU'):
            return humanize.naturalsize(number, gnu=True)


@register.filter(name='prevcurnext')
def prevcurnext(orig):
    """ From an iterable, return another 3-tuples one for prev/next access.

    Reference: http://stackoverflow.com/a/10078809/654755
    How elegant (and expensive) it is.
    """

    if isinstance(orig, QuerySet):
        # Too bad QuerySet doesn't support negative indexing,
        # this makes this filter really very expensive.
        orig = list(orig)

    if len(orig) == 1:
        return (
            [(None, orig[0], None)]
        )

    return (
        [(None, orig[0], orig[1])]
        + zip(orig, orig[1:], orig[2:])
        + [(orig[-2], orig[-1], None)]
    )
