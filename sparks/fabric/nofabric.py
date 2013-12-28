# -*- coding: utf8 -*-
"""

Mini fabric-like runners and compatible API.

Used in :program:`1nstall` and when fabric is not available.

.. warning:: they're really MINIMAL, and won't work as well as fabric does.

"""

import logging
import subprocess

LOGGER = logging.getLogger(__name__)


class _AttributeString(str):
    """ Directly taken from Fabric's operations. Clever. """

    @property
    def stdout(self):
        return str(self)
        
def exists(filename, *a, **kw):

    try:
        exists = os.path.exists(filename)
      
    except Exception as e:
        output           = _AttributeString(e)
        output.command   = command
        output.failed    = True
        output.succeeded = False

    else:
        output.command   = command
        output.failed    = False
        output.succeeded = True

    return output

def run(command, *a, **kw):

    try:
        output = _AttributeString(subprocess.check_output(command,
                                  shell=kw.pop('shell', True),
                                  universal_newlines=True))

    except subprocess.CalledProcessError as e:
        output           = _AttributeString(e.output)
        output.command   = command
        output.failed    = True
        output.succeeded = False

    else:
        output.command   = command
        output.failed    = False
        output.succeeded = True

    return output


def sudo(command, *a, **kw):
    return run('sudo %s' % command, *a, **kw)


local = run
