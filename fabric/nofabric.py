# -*- coding: utf8 -*-
"""

Mini fabric-like runners and compatible API.

Used in :program:`1nstall` and when fabric is not available.

.. warning:: they're really MINIMAL, and won't work as well as fabric does.

"""

import subprocess
from ..foundations.classes import SimpleObject


def _run(command, *a, **kw):

    output = SimpleObject()

    try:
        #print '>> running', command
        output.output = subprocess.check_output(command,
                                                shell=kw.pop('shell', True))

    except subprocess.CalledProcessError, e:
        output.command   = e.cmd
        output.output    = e.output
        output.failed    = True
        output.succeeded = False

    else:
        output.failed    = False
        output.succeeded = True

    return output


def _sudo(command, *a, **kw):
    return _run('sudo %s' % command, *a, **kw)

_local = _run
