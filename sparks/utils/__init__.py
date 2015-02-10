# -*- coding: utf-8 -*-
u"""
Copyright 2012-2015 Olivier Cortès <oc@1flow.io>.

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

import logging
import time as time
from humanize.time import naturaldelta


LOGGER = logging.getLogger(__name__)


def stats_datetime():
    """ Generate a string from now, suitable for benchmark() calls. """

    return pytime.strftime('%Y-%m-%d %H:%M')


class benchmark(object):

    """ Simple benchmark context-manager class.

    http://dabeaz.blogspot.fr/2010/02/context-manager-for-timing-benchmarks.html  # NOQA
    """

    def __init__(self, name=None):
        """ Oh my, pep257, this is an init method. """

        self.name = name or u'Generic benchmark'

    def __enter__(self):
        """ Start the timer. """

        self.start   = time.time()
        self.dtstart = stats_datetime()

    def __exit__(self, ty, val, tb):
        """ Stop the timer and display a logging message with elapsed time. """

        LOGGER.info("%s started %s, ran in %s.", self.name, self.dtstart,
                    naturaldelta(time.time() - self.start))
        return False