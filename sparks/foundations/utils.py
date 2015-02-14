# -*- coding: utf-8 -*-
""" Sparks utils. """

import uuid


def unique_hash(only_letters=False):
    """ Return a unique hash (an UUID), possibly with only letters. """

    if only_letters:
        return ''.join((chr(int(x) + 97) if x.isdigit() else x)
                       for x in uuid.uuid4().hex)
    return uuid.uuid4().hex


def combine_dicts(dict1, dict2):
    """ Some kind of recursive `update()` for dictionnaries.

    Used in place of `update()`, when you know the dicts have sub-dicts,
    potentially with same names, and you want sub-dicts to be merged (the
    way `update()` does) instead of one overwring the other.

    .. warning: like in `update()`, :param:`dict2` values take precedence
        over the ones from :param:`dict1`.
    """

    # source: http://stackoverflow.com/a/7205234/654755

    output = {}

    for item, value in dict1.iteritems():
        if item in dict2:
            if isinstance(dict2[item], dict):
                output[item] = combine_dicts(value, dict2.pop(item))
            # else:
            #   will be merged by second loop.

        else:
            output[item] = value

    for item, value in dict2.iteritems():
        output[item] = value

    return output
