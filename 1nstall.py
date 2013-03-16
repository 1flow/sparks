#!/usr/bin/env python

import sys
import os

try:
    from sparks import fabric as sf

except ImportError:
    from . import fabric as sf

if sf.lsb_release:
    if sf.is_vm:
        if not os.path.exists(os.path.expanduser('~/Dropbox')):
            if sf.is_parallel:
                sf._run('ln -sf /media/psf/Home/Dropbox ~/')

        # TODO: implement for vmware.

    else:
        if os.path.exists('/usr/bin/dropbox'):
            # OK, just continue.
            pass

        else:
            # TODO: install dropbox automatically.
            print '>> please install dropbox, set it up, and relaunch.'
            sys.exit(1)

    for filename in ('bashrc', 'ssh'):
        sf._run('ln -sf %s ~/.%s' % (sf.dotfiles('dot.%s' % filename),
                filename))

    sf._sudo('apt-get update')
    sf._sudo('apt-get install -y --force-yes gdebi python-pip ssh '
             'python-all-dev build-essential')
    sf._sudo('pip install fabric')

else:
    sf._sudo('ruby -e "$(curl -fsSL https://raw.github.com/mxcl/homebrew/go)"')

os.system('cd ~/Dropbox/configuration; fab -H localhost myenv')
