# -*- coding: utf8 -*-


class SimpleObject:
    def __init__(self, from_dict=None):
        if from_dict:
            for key, value in from_dict.iteritems():
                setattr(self, key, value)

    def __str__(self):
        return ''.join(('%s: %s' % (k, getattr(self, k))) for k in dir(self))

    def __getattr__(self, key):
        try:
            return getattr(self.output, key)

        except AttributeError:
            raise AttributeError("SimpleObject instance has no "
                                 "attribute '%s'" % key)
