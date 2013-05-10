# -*- coding: utf8 -*-

import logging
from threading import Thread

LOGGER = logging.getLogger(__name__)


class SimpleObject:
    def __init__(self, from_dict=None):
        if from_dict:
            for key, value in from_dict.items():
                setattr(self, key, value)

    def __str__(self):
        return ''.join(('%s: %s' % (k, getattr(self, k))) for k in dir(self))

    def __getattr__(self, key):

        if hasattr(self, 'output'):
            return getattr(self.output, key)

        raise AttributeError("SimpleObject instance has no "
                             "attribute '%s'" % key)


class BatcherThread(Thread):
    """ Enhanced version of the classic Python Thread.
        Each instance will add itself to its ``class.threads``.

        The class has a :meth:`join_all` method allowing to wait for
        all instances to terminate.

        .. versionadded:: 1.17
    """

    threads = []

    @classmethod
    def join_all(cls, parallel=False):
        LOGGER.debug('%s: joining %sthreads %s', cls.__name__,
                     'all ' if parallel else '',
                     ', '.join(t.name for t in cls.threads
                     if (parallel or not t.parallel)
                     and t.__class__ == cls))

        for t in cls.threads:
            if t.parallel and not parallel:
                continue

        if t.__class__ == cls:
            t.join()

    def __init__(self, target, *a, **kw):
        self.parallel = kw.pop('parallel', False)
        super(BatcherThread, self).__init__(target=target, *a, **kw)
        self.__class__.threads.append(self)

    def start(self):
        """ This method returns the current instance for easier initialization,
            eg. writing ``t = BatcherThread(target…).start()`` is sufficient.
        """

        super(BatcherThread, self).start()
        return self
