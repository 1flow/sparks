# -*- coding: utf-8 -*-
"""
Copyright 2013-2014 Olivier Cortès <oc@1flow.io>.

This file is part of the sparks project.

It rassembles template tags I use in multiple projects.

Reference documentation:
http://www.christianfaur.com/color/
http://www.christianfaur.com/color/Site/Picking%20Colors.html

And then:
http://stackoverflow.com/q/3116260/654755
http://ux.stackexchange.com/q/8297

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

import re
import logging
import difflib
import mistune

from math import pow

from sparks.django.templatetags import register

LOGGER = logging.getLogger(__name__)

register = template.Library()

# ———————————————————————————————————————————————————————————— Letters & Colors

letters_colors = {
    u'a': ((0, 0, 180), u'rgba(0, 0, 180, 1)', u'blue'),
    u'b': ((175, 13, 102), u'rgba(175, 13, 102, 1)', u'red-violet'),
    u'c': ((146, 248, 70), u'rgba(146, 248, 70, 1)', u'green-yellow'),
    u'd': ((255, 200, 47), u'rgba(255, 200, 47, 1)', u'yellow-orange'),
    u'e': ((255, 118, 0), u'rgba(255, 118, 0, 1)', u'orange'),

    # Original f & g, not used because grey means "disabled"
    # and G is not visible enough when opacity < 1.
    #
    #    u'f': ((185, 185, 185), u'rgba(185, 185, 185, 1)', u'light-gray'),
    #    u'g': ((235, 235, 222), u'rgba(235, 235, 222, 1)', u'off-white'),
    #
    # Instead, we use w & y colors, which are the most near on the graph.

    u'f': ((255, 152, 213), u'rgba(255, 152, 213, 1)', u'pink'),
    u'g': ((175, 200, 74), u'rgba(175, 200, 74, 1)', u'olive-green'),
    u'h': ((100, 100, 100), u'rgba(100, 100, 100, 1)', u'gray'),
    u'i': ((255, 255, 0), u'rgba(255, 255, 0, 1)', u'yellow'),
    u'j': ((55, 19, 112), u'rgba(55, 19, 112, 1)', u'dark-purple'),
    u'k': ((255, 255, 150), u'rgba(255, 255, 150, 1)', u'light-yellow'),
    u'l': ((202, 62, 94), u'rgba(202, 62, 94, 1)', u'dark-pink'),
    u'm': ((205, 145, 63), u'rgba(205, 145, 63, 1)', u'dark-orange'),
    u'n': ((12, 75, 100), u'rgba(12, 75, 100, 1)', u'teal'),
    u'o': ((255, 0, 0), u'rgba(255, 0, 0, 1)', u'red'),
    u'p': ((175, 155, 50), u'rgba(175, 155, 50, 1)', u'dark-yellow'),
    u'q': ((0, 0, 0), u'rgba(0, 0, 0, 1)', u'black'),
    u'r': ((37, 70, 25), u'rgba(37, 70, 25, 1)', u'dark-green'),
    u's': ((121, 33, 135), u'rgba(121, 33, 135, 1)', u'purple'),
    u't': ((83, 140, 208), u'rgba(83, 140, 208, 1)', u'light-blue'),
    u'u': ((0, 154, 37), u'rgba(0, 154, 37, 1)', u'green'),
    u'v': ((178, 220, 205), u'rgba(178, 220, 205, 1)', u'cyan'),
    u'w': ((255, 152, 213), u'rgba(255, 152, 213, 1)', u'pink'),
    u'x': ((0, 0, 74), u'rgba(0, 0, 74, 1)', u'dark blue'),
    u'y': ((175, 200, 74), u'rgba(175, 200, 74, 1)', u'olive-green'),
    u'z': ((63, 25, 12), u'rgba(63, 25, 12, 1)', u'red-brown'),
}

html_letters_re = re.compile(ur'[^\w]', re.UNICODE | re.IGNORECASE)


@register.simple_tag
def html_first_letters(name, number=1):
    """ Return one or more significant letter(s) from a name. """

    try:
        # Try to get the capitalized letters to make a nice name.
        capitalized = ''.join(c for c in name if c.isupper() or c.isdigit())

    except:
        # If that fails, just start with the full name.
        cleaned = html_letters_re.sub(u'', name)

    else:
        caplen = len(capitalized)

        # If it succeeded, make sure we have enough letters
        if caplen > 0:

            # If we don't have enough letters, take
            # what's left after the last capital.
            if caplen < number:
                capitalized += name[name.index(capitalized[-1]) + 1:]

            cleaned = html_letters_re.sub(u'', capitalized)

        else:
            cleaned = html_letters_re.sub(u'', name)

    if len(cleaned) == 0:
        number = 3
        cleaned   = u';-)'

    if number > len(cleaned):
        number = 1

    try:
        return cleaned[:number].title()

    except:
        # OMG… Unicode characters everywhere…
        return cleaned[:number]


@register.simple_tag
def html_background_color_for_name(name, opacity=1):
    """ Return a background color suitable for a name.

    The color is returned as a string like ``rgba(nn, nn, nn, xx)`` where
    ``xx`` will be replaced verbatim by the :param:`opacity` argument.
    """

    name = html_letters_re.sub(u'', name)

    try:
        letter = name[0].lower()

    except:
        # OMG… Unicode characters everywhere…
        letter = u'a'

    try:
        return letters_colors[letter][1].replace(u', 1)',
                                                 u', {0})'.format(opacity))

    except:
        # Still, some unicode characters can
        # lower() but are not in the table.
        return letters_colors[u'a'][1].replace(u', 1)',
                                               u', {0})'.format(opacity))


@register.simple_tag
def html_foreground_color_for_name(name):
    """ Return a foreground color (white or black) suitable for a name.

    The color will be returned as a string (eg. ``white`` or ``black``).
    """

    name = html_letters_re.sub(u'', name)

    try:
        letter = name[0].lower()

    except:
        # OMG… Unicode characters everywhere…
        letter = u'a'

    try:
        R, G, B = letters_colors[letter][0]

    except:
        # Still, some unicode characters can
        # lower() but are not in the table.
        R, G, B = letters_colors[u'a'][0]

    Y = (0.2126 * pow(R / 255, 2.2)
         + 0.7151 * pow(G / 255, 2.2)
         + 0.0721 * pow(B / 255, 2.2))

    return u'white' if Y <= 0.18 else u'black'
