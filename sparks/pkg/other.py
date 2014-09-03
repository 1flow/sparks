# -*- coding: utf-8 -*-

from ..fabric import QUIET, run, sudo
from ..fabric.utils import list_or_split
from .common import is_installed, search

# ---------------------------------------------- NPM package management

# TODO: npm_usable


def npm_is_installed(pkg):
    """ Return ``True`` if a given NodeJS package is installed. """

    return is_installed("npm list -i %s | grep ' %s@'" % (pkg, pkg))


def npm_add(pkgs):
    for pkg in list_or_split(pkgs):
        if not npm_is_installed(pkg):
            run('npm install %s' % pkg, quiet=QUIET)


def npm_search(pkgs):
    # 2>&1 is necessary to catch the http/NAME (they are on stderr)
    for pkg in list_or_split(pkgs):
        yield search("npm search %s 2>&1 | grep -vE '^(npm |NAME|No match).*' "
                     "| sed -e 's/ =.*$//g'" % pkg)

# ---------------------------------------------- GEM package management

# TODO: gem_usable


def gem_is_installed(pkg):
    """ Return ``True`` if a given Ruby gem is installed. """

    return is_installed('gem list -i %s' % pkg)


def gem_add(pkgs):
    for pkg in list_or_split(pkgs):
        if not gem_is_installed(pkg):
            run('gem install %s' % pkg, quiet=QUIET)


def gem_search(pkgs):
    for pkg in list_or_split(pkgs):
        yield search("gem search -r %s 2>&1 | grep -vE '^(\*\*\*|$)'" % pkg)
