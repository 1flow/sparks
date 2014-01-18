#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    This script is meant to bootstrap a brand new machine when I can't
    bootstrap it from another one, or when it will be used as one of my
    *principal* machines, aka the machine from which I deploy others.

"""
import sys
import os
import pwd
import logging

LOGGER = logging.getLogger(__name__)

if __package__ is None:
    # See ./fabfile.py for explanations
    sys.path.append(os.path.expanduser('~/Dropbox'))

from sparks import fabric as sf
from sparks.fabric import utils


# If we are running this script more than once, Fabric is likely to be 
# installed at calls+1. We set `host_string` to localhost to avoid it
# stopping the automatic installation for asking us the obvious answer.
try:
    sf.env.host_string = 'localhost'

except AttributeError:
    pass

DROPBOX_PATH = os.path.expanduser('~/Dropbox')


@sf.with_remote_configuration
def main(remote_configuration=None):
    if remote_configuration.lsb:
        if os.path.exists(DROPBOX_PATH):
            if remote_configuration.is_vm:
                if not os.path.exists(DROPBOX_PATH):
                    if remote_configuration.is_parallel:
                        sf.nofabric.run('ln -sf /media/psf/Home/Dropbox ~/')

                    else:
                        # TODO: implement for vmware.
                        pass

            for filename in ('bashrc', 'ssh'):
                sf.nofabric.run('ln -sf %s ~/.%s' % (utils.dotfiles('dot.%s'
                                % filename), filename))

        sf.nofabric.sudo('apt-get update')
        sf.nofabric.sudo('apt-get install -y --force-yes gdebi python-pip ssh '
                         'python-all-dev build-essential')

    else:
        # TODO: there's work to do here: install Xcode & CLI tools for Xcode.
        sf.nofabric.run('ruby -e "$(curl -fsSL '
                         'https://raw.github.com/mxcl/homebrew/go)"')
        sf.nofabric.run('brew update; brew install python pip')

    sf.nofabric.sudo('pip install fabric')

    if pwd.getpwuid(os.getuid()).pw_name in ('olive', 'karmak23'):
        task = 'myenv'
    else:
        task = 'dev'

    command = 'cd ~/ ; fab -f "{0}/fabfile.py" -H localhost {1}'.format(
        os.path.dirname(sys.argv[0]), task)

    LOGGER.info(u'Now running "%s"', command)
    os.system(command)

if __name__ == '__main__':
    main()
