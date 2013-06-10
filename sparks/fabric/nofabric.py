# -*- coding: utf8 -*-
"""

Mini fabric-like runners and compatible API.

Used in :program:`1nstall` and when fabric is not available.

.. warning:: they're really MINIMAL, and won't work as well as fabric does.

"""

import subprocess


class _AttributeString(str):
    """ Directly taken from Fabric's operations. Clever. """

    @property
    def stdout(self):
        return str(self)


def run(command, *a, **kw):

    output = _AttributeString()

    output.command = command

    try:
        #print '>> running', command
        output = subprocess.check_output(command,
                                         shell=kw.pop('shell', True),
                                         universal_newlines=True)

    except subprocess.CalledProcessError as e:
        output           = e.output
        output.failed    = True
        output.succeeded = False

    else:
        output.failed    = False
        output.succeeded = True

    return output


def sudo(command, *a, **kw):
    return run('sudo %s' % command, *a, **kw)


local = run
