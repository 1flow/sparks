# -*- coding: utf-8 -*-
""" Sparks utils. """

import uuid


def unique_hash(only_letters=False):
    """ Return a unique hash (an UUID), possibly with only letters. """

    if only_letters:
        return ''.join((chr(int(x) + 97) if x.isdigit() else x)
                       for x in uuid.uuid4().hex)
    return uuid.uuid4().hex


def combine_dicts(dict1, dict2, *args):
    u""" Some kind of recursive `update()` for dictionnaries.

    Used in replacement of `update()`, when you know the dicts have
    sub-dicts in their values, potentially with same keys names, and
    you want sub-dicts to be also merged the way `update()` does,
    instead beiing overwritten.

    .. warning: like in dict standard `update()` method, :param:`dict2`
        values take precedence over the ones from :param:`dict1`. In case
        you give more than 2 dictionnaries, the last takes precedence
        over the previous, and so on (eg. “right-most priority”).
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

    if args:
        if len(args) > 1:
            return combine_dicts(output, args[0], *args[1:])

        return combine_dicts(output, args[0])

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
