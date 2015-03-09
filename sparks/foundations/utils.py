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


def jaccard_similarity(string1, string2):
    """ Return the Jaccard similarity of 2 strings.

    Strings should be as simple as possible. No stemming, no bells,
    no whistles. This function is very bare, but does the job if you
    need simple operations.

    Similarity belongs to [0.0, 1.0], 1.0 means its exact replica (whatever
    words order).
    """

    a = set(string1.split())
    b = set(string2.split())

    similarity = float(
        len(a.intersection(b)) * 1.0
        / len(a.union(b)))

    return similarity


def lookahead(iterable):
    """ Yield (item, item_is_last) from iterable. """

    # Cf. http://stackoverflow.com/a/1630350/654755

    it = iter(iterable)

    # next(it) in Python 3
    last = it.next()

    for val in it:
        yield last, False
        last = val

    yield last, True
