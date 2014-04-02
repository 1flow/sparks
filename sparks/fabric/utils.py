# -*- coing: utf-8 -*-

import os
import logging

from . import with_remote_configuration, exists, local, run

LOGGER = logging.getLogger(__name__)


# ======================================================================= Utils


SPARKS_DOTFILES_PATH = os.environ.get('SPARKS_DOTFILES_PATH', None)


if SPARKS_DOTFILES_PATH is None:
    if os.path.exists(os.path.expanduser(u'~/Dropbox/configuration/dotfiles')):
        LOGGER.info(u'Using default value of "~/Dropbox/configuration/dotfiles"'
                    u'for SPARKS_DOTFILES_PATH.')
        SPARKS_DOTFILES_PATH = 'Dropbox/configuration/dotfiles'

    else:
       LOGGER.info(u'Please define shell variable SPARKS_DOTFILES_PATH '
                   u'if you would like to benefit from sparks personal '
                   u'deployment facilities.')
else:
    LOGGER.info(u'Using SPARKS_DOTFILES_PATH="%s".', SPARKS_DOTFILES_PATH)


def list_or_split(pkgs):
    try:
        return (p for p in pkgs.split() if p not in ('', None, ))

    except AttributeError:
        #if type(pkgs) in (types.TupleType, types.ListType):
        return pkgs


def dsh_to_roledefs():
    dsh_group = os.path.expanduser('~/.dsh/group')
    roles     = {}

    if os.path.exists(dsh_group):
        for entry in os.listdir(dsh_group):
            if entry.startswith('.'):
                continue

            fullname = os.path.join(dsh_group, entry)

            if os.path.isfile(fullname):
                roles[entry] = [line for line
                                in open(fullname).read().split()
                                if line != '']

    return roles


def symlink(source, destination, overwrite=False, locally=False):

    rm_prefix = ''

    if exists(destination):
        if overwrite:
            rm_prefix = 'rm -rf "%s"; ' % destination

        else:
            return

    command = '%s ln -sf "%s" "%s"' % (rm_prefix, source, destination)

    local(command) if locally else run(command)


# ========================================================== User configuration


@with_remote_configuration
def tilde(directory=None, remote_configuration=None):
    """ Just a handy shortcut. """

    return os.path.join(remote_configuration.tilde, directory or '')


def dotfiles(filename):
    """ Where are my dotfiles? (relative from $HOME).

        .. note:: use with :func:`tilde` to get full path.
            Eg. ``tilde(dotfiles('dot.bashrc'))`` =>
            ``/home/olive/Dropbox/configuration/dotfiles/dot.bashrc``.
    """

    return os.path.join(SPARKS_DOTFILES_PATH, filename)
