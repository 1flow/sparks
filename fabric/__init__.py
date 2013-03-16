# -*- coding: utf8 -*-

import os
import subprocess

try:
    import lsb_release

except ImportError:
    # Not a Linux platform. Probably OSX.
    lsb_release = None

try:
    from fabric.api              import run, sudo, local
    from fabric.contrib.files    import exists
    from fabric.context_managers import cd
    from fabric.colors           import green

    _wrap_fabric = False

except ImportError:
    _wrap_fabric = True
# =============================================================== Utils


class SimpleObject:
    def __init__(self, from_dict=None):
        if from_dict:
            for key, value in from_dict.iteritems():
                setattr(self, key, value)


def list_or_split(pkgs):
    try:
        return (p for p in pkgs.split() if p not in ('', None, ))

    except AttributeError:
        #if type(pkgs) in (types.TupleType, types.ListType):
        return pkgs


def dsh_to_roledefs():
    dsh_group = tilde('.dsh/group')
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


def tilde(directory=None):
    """ Just a handy shortcut. """

    return os.path.expanduser('~/%s' % (directory or ''))


def symlink(source, destination, overwrite=False, locally=False):

    prefix = ''

    if exists(destination):
        if overwrite:
            prefix = 'rm -rf "%s"; ' % destination

        else:
            return

    command = '%s ln -sf "%s" "%s"' % (prefix, source, destination)

    local(command) if locally else run(command)


# Mini fabric-like runners. Used in 1nstall and when fabric is not available.
# WARNING: they're really MINIMAL, and won't work as well as fabric does.
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

if _wrap_fabric:
    # If fabric is not available, this means we are imported from 1nstall.py.
    # Everything will fail except the base system detection. We define the bare
    # minimum for it to work on a local Linux/OSX system.
    run   = _run
    local = _local
    sudo  = _sudo

# ========================================== Package management helpers


def silent_sudo(command):
    #with settings(hide('warnings', 'running',
    #        'stdout', 'stderr'), warn_only=True):
    return sudo(command, quiet=True, warn_only=True)


def is_installed(test_installed_command):
    """ Return ``True`` if :param:`test_installed_command` succeeded. """

    return silent_sudo(test_installed_command).succeeded


def search(search_command):
    return sudo(search_command, quiet=True)

# ---------------------------------------------- PIP package management


def pip_perms():
    """ Apply correct permissions on /usr/local/lib/*. Thanks PIP :-/ """

    print(green('Restoring correct permissions in /usr/local/lib…'))
    silent_sudo('find /usr/local/lib -type f -print0 '
                '| xargs -0 -n 1024 chmod 644')
    silent_sudo('find /usr/local/lib -type d -print0 '
                '| xargs -0 -n 1024 chmod 755')


def pip_is_installed(pkg):
    """ Return ``True`` if a given Python module is installed via PIP. """

    return is_installed("pip freeze | grep -i '%s=='" % pkg)


def pip_add(pkgs):
    # Go to a neutral location before PIP tries to "mkdir build"
    # WARNING: this could be vulnerable to symlink attack when we
    # force unlink of hard-coded build/, but in this case PIP is
    # vulnerable during the install phase too :-/
    with cd('/var/tmp'):
        installed = False
        for pkg in list_or_split(pkgs):
            if not pip_is_installed(pkg):
                sudo("pip install -U %s " % pkg)
                installed = True

        if installed:
            silent_sudo('rm -rf build')
            pip_perms()


def pip_search(pkgs):
    for pkg in list_or_split(pkgs):
        yield search("pip search %s" % pkg)

# ---------------------------------------------- NPM package management


def npm_is_installed(pkg):
    """ Return ``True`` if a given NodeJS package is installed. """

    return is_installed("npm list -i %s | grep ' %s@'" % (pkg, pkg))


def npm_add(pkgs):
    for pkg in list_or_split(pkgs):
        if not npm_is_installed(pkg):
            sudo('npm install %s' % pkg)


def npm_search(pkgs):
    # 2>&1 is necessary to catch the http/NAME (they are on stderr)
    for pkg in list_or_split(pkgs):
        yield search("npm search %s 2>&1 | grep -vE '^(npm |NAME).*' "
                     "| sed -e 's/ =.*$//g'" % pkg)

# ---------------------------------------------- GEM package management


def gem_is_installed(pkg):
    """ Return ``True`` if a given Ruby gem is installed. """

    return is_installed('gem list -i %s' % pkg)


def gem_add(pkgs):
    for pkg in list_or_split(pkgs):
        if not gem_is_installed(pkg):
            sudo('gem install %s' % pkg)


def gem_search(pkgs):
    for pkg in list_or_split(pkgs):
        yield search("gem search -r %s 2>&1 | grep -vE '^(\*\*\*|$)'" % pkg)

# ---------------------------------------------- APT package management


def apt_usable():
    return lsb is not None


def apt_is_installed(pkg):
    """ Return ``True`` if a given package is installed via APT/dpkg. """

    # OMG, this is so ugly. but `dpkg -l %s` will answer
    # 'un <package> uninstalled' + exit 0 if not installed.
    return is_installed('dpkg -l | grep " %s "' % pkg)


def apt_update():
    """ Update APT packages list. """

    sudo('apt-get update -q')


def apt_upgrade():
    """ Upgrade outdated Debian packages. """

    sudo('apt-get -u dist-upgrade -q --yes --force-yes')


def apt_add(pkgs):
    for pkg in list_or_split(pkgs):
        if not apt_is_installed(pkg):
            sudo('apt-get -q install --yes --force-yes %s' % pkg)


def apt_del(pkgs):
    for pkg in list_or_split(pkgs):
        if apt_is_installed(pkg):
            sudo('apt-get -q remove --purge --yes --force-yes %s' % pkg)


def ppa(src):
    sudo('add-apt-repository -y "%s"' % src)
    apt_update()


def key(key):
    """ Add a GPG key to the local APT key database. """

    sudo('wget -q -O - %s | apt-key add -' % key)


def ppa_pkg(src, pkgs, check_path=None):

    if check_path and exists(check_path):
        return

    ppa(src)
    apt_add(pkgs)


def apt_search(pkgs):
    for pkg in list_or_split(pkgs):
        yield search("apt-cache search %s" % pkg)


# --------------------------------------------- Brew package management

def brew_usable():
    return lsb is None


def brew_is_installed(pkg):
    """ Return ``True`` if a given application is installed via Brew (on OSX).
    """

    return is_installed('brew list %s >/dev/null 2>&1' % pkg)


def brew_add(pkgs):
    """ Add a local package via Homebrew (on OSX).

        .. note:: we always use FORCE_UNSAFE_CONFIGURE=1 to avoid errors::

            checking whether mknod can create fifo without root privileges... configure: error: in `/private/tmp/coreutils-zCgv/coreutils-8.21':
            configure: error: you should not run configure as root (set FORCE_UNSAFE_CONFIGURE=1 in environment to bypass this check)
            See `config.log' for more details
            READ THIS: https://github.com/mxcl/homebrew/wiki/troubleshooting
    """

    for pkg in list_or_split(pkgs):
        if not brew_is_installed(pkg):
            sudo('FORCE_UNSAFE_CONFIGURE=1 brew install %s' % pkg)


def brew_del(pkgs):
    for pkg in list_or_split(pkgs):
        if brew_is_installed(pkg):
            sudo('brew remove %s' % pkg)


def brew_update():
    """ Update Homebrew formulas. """

    sudo('brew update')


def brew_upgrade():
    """ Upgrade outdated brew packages. """

    sudo('brew upgrade')


def brew_search(pkgs):
    for pkg in list_or_split(pkgs):
        yield search("brew search %s 2>&1 | grep -v 'No formula found for' "
                     "| tr ' ' '\n' | sort -u" % pkg)


# ------------------------------------------ Generic package management


def pkg_is_installed(pkg):
    if lsb:
        return apt_is_installed(pkg)
    else:
        return brew_is_installed(pkg)


def pkg_add(pkgs):
    if lsb:
        return apt_add(pkgs)
    else:
        return brew_add(pkgs)


def pkg_del(pkgs):
    if lsb:
        return apt_del(pkgs)
    else:
        return brew_del(pkgs)


def pkg_update():
    if lsb:
        return apt_update()
    else:
        return brew_update()


def pkg_upgrade():
    if lsb:
        return apt_upgrade()
    else:
        return brew_upgrade()

# ============================================ Local system information

uname = SimpleObject(from_dict=dict(zip(
                                    ('sysname', 'nodename', 'release',
                                        'version', 'machine'),
                                    os.uname())))

# TODO: implement me (and under OSX too).
is_vmware = False

# NOTE: this test could fail in VMs where nothing is mounted from the host.
# In my own configs, this never occurs, but who knows.
# TODO: check this works under OSX too, or enhance the test.
is_parallel = _run('mount | grep prl_fs', quiet=True, warn_only=True).succeeded

is_vm = is_parallel or is_vmware

if lsb_release:
    lsb = SimpleObject(from_dict=lsb_release.get_lsb_information())
else:
    lsb = None


def dotfiles(filename):
    """ Where are my dotfiles? (relative from $HOME).

        .. note:: use with :func:`tilde` to get full path.
            Eg. ``tilde(dotfiles('dot.bashrc'))`` =>
            ``/home/olive/Dropbox/dotfiles/dot.bashrc``.
    """

    return os.path.join('Dropbox/configuration/dotfiles', filename)
