# -*- coding: utf-8 -*-

import uuid


def unique_hash(only_letters=False):
    if only_letters:
        return ''.join((chr(int(x) + 97) if x.isdigit() else x)
                       for x in uuid.uuid4().hex)
    return uuid.uuid4().hex
