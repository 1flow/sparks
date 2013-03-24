# -*- coding: utf8 -*-


class SimpleObject:
    def __init__(self, from_dict=None):
        if from_dict:
            for key, value in from_dict.iteritems():
                setattr(self, key, value)

