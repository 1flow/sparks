#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    This script is meant to bootstrap a brand new machine when I can't
    bootstrap it from another one, or when it will be used as one of my
    *principal* machines, aka the machine from which I deploy others.

"""
import sys
import os

if __package__ is None:
    # See ./fabfile.py for explanations
    sys.path.append(os.path.expanduser('~/Dropbox'))

from sparks import fabric as sf


@sf.with_remote_configuration
def main(remote_configuration=None):
    if remote_configuration.lsb_release:
        if remote_configuration.is_vm:
            if not os.path.exists(os.path.expanduser('~/Dropbox')):
                if remote_configuration.is_parallel:
                    sf.nofabric._run('ln -sf /media/psf/Home/Dropbox ~/')

                else:
                    # TODO: implement for vmware.
                    pass

        for filename in ('bashrc', 'ssh'):
            sf.nofabric._run('ln -sf %s ~/.%s' % (sf.dotfiles('dot.%s'
                             % filename), filename))

        sf.nofabric.sudo('apt-get update')
        sf.nofabric.sudo('apt-get install -y --force-yes gdebi python-pip ssh '
                         'python-all-dev build-essential')
        sf.nofabric.sudo('pip install fabric')

    else:
        # TODO: there's work to do here: install Xcode & CLI tools for Xcode.
        sf.nofabric.sudo('ruby -e "$(curl -fsSL '
                         'https://raw.github.com/mxcl/homebrew/go)"')
        sf.nofabric.sudo('brew update; brew install python pip')

    os.system('cd ~/Dropbox/configuration; fab -H localhost myenv')

if __name__ == '__main__':
    main()
