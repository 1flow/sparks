# -*- coding: utf8 -*-

import os
import sys
import uuid
import logging

from fabric.api              import env, run, sudo, local, task
from fabric.operations       import get, put
from fabric.contrib.console  import confirm
from fabric.contrib.files    import contains, append, exists, sed
from fabric.context_managers import cd, settings, hide
from fabric.colors           import yellow, cyan

if __package__ is None:
    # See #2 comment of http://stackoverflow.com/a/11537218/654755
    # and http://www.python.org/dev/peps/pep-0366/
    sys.path.append(os.path.expanduser('~/Dropbox'))

from sparks import pkg, fabric as sf

# ===================================================== Local variables

LOGGER = logging.getLogger(__name__)
local_osx_apps = '~/Downloads/{Mac,OSX}*/'
central_osx_apps = 'duncan:oliviercortes.com/sparks/osx'


# ================================================ Fabric configuration

env.use_ssh_config = True
env.roledefs       = sf.dsh_to_roledefs()


def info(text):
    print(cyan(text))

# ====================================================== Fabric targets

# -------------------------------------- Standalone application recipes


@sf.with_remote_configuration
def install_chrome(remote_configuration=None):
    """ Install Google Chrome via .DEB packages from Google. """

    if remote_configuration.is_osx:
        if not exists('/Applications/Google Chrome.app'):
            # TODO: implement me.
            info("Please install Google Chrome manually.")

    else:
        if exists('/usr/bin/google-chrome'):
            return

        sf.key('https://dl-ssl.google.com/linux/linux_signing_key.pub')
        append('/etc/apt/sources.list.d/google-chrome.list',
               'deb http://dl.google.com/linux/chrome/deb/ stable main',
               use_sudo=True)
        pkg.apt_update()
        pkg.apt_add('google-chrome-stable')


@sf.with_remote_configuration
def install_skype(remote_configuration=None):
    """ Install Skype 32bit via Ubuntu partner repository. """

    if remote_configuration.is_osx:
        if not exists('/Applications/Skype.app'):
            # TODO: implement me.
            info("Please install %s manually." % yellow('Skype'))

    else:
        sf.ppa_pkg('deb http://archive.canonical.com/ubuntu %s partner'
                   % remote_configuration.lsb.CODENAME,
                   'skype', '/usr/bin/skype')


@sf.with_remote_configuration
def install_sublime(overwrite=False, remote_configuration=None):
    """ Install Sublime Text 2 in /opt via a downloaded .tar.bz2. """

    if remote_configuration.is_osx:
        if not exists('/Applications/Sublime Text.app'):
            # TODO: implement me.
            info("Please install Sublime Text manually.")

    else:
        if overwrite or not exists('/opt/sublime2'):
            if sf.uname.machine == 'x86_64':
                url = 'http://c758482.r82.cf2.rackcdn.com/' \
                      + 'Sublime%20Text%202.0.1%20x64.tar.bz2'

            else:
                url = 'http://c758482.r82.cf2.rackcdn.com/' \
                      + 'Sublime%20Text%202.0.1.tar.bz2'

            run('wget -q -O /var/tmp/sublime.tar.bz2 %s' % url)

            with cd('/opt'):
                sudo('tar -xjf /var/tmp/sublime.tar.bz2')
                sudo('mv "Sublime Text 2" sublime2')

        executable = sf.tilde('bin/sublime')

        if overwrite or not exists(executable):
            run('echo -e "#!/bin/sh\ncd /opt/sublime2\n./sublime_text\n" > %s'
                % executable)

        # Always be sure the executable *IS* executable ;-)
        run('chmod 755 %s' % executable, quiet=True)

        if overwrite or not exists('/usr/share/applications/sublime2.desktop'):
            put(os.path.join('Dropbox', 'configuration', 'data',
                'sublime2.desktop'),
                '/usr/share/applications', use_sudo=True)


@sf.with_remote_configuration
def install_homebrew(remote_configuration=None):
    """ Install Homebrew on OSX from http://mxcl.github.com/homebrew/ """

    if not remote_configuration.is_osx:
        return

    if exists('/usr/local/bin/brew'):

        if confirm('Update Brew Formulæ?', default=False):
            pkg.brew_update()

        if confirm('Upgrade outdated Brew packages?',
                   default=False):
            pkg.brew_upgrade()

    else:
        sudo('ruby -e "$(curl -fsSL https://raw.github.com/mxcl/homebrew/go)"')

        sudo('brew doctor')
        pkg.brew_add(('git', ))

        # TODO: implement this.
        info('Please install OSX CLI tools for Xcode manually.')

        if confirm('Is the installation OK?'):
            pkg.brew_update()

    LOGGER.warning('You still have to install Xcode and its CLI tools.')


@sf.with_remote_configuration
def install_1password(remote_configuration=None):
    """ NOT IMPLEMENTED: Install 1Password. """

    if remote_configuration.is_osx:
        if not exists('/Applications/1Password.app'):
            info('Please install %s manually.' % yellow('1Password'))

    else:
        # TODO: implement me
        pkg.apt_add('wine')


@sf.with_remote_configuration
def install_powerline(remote_configuration=None):
    """ Install the Ubuntu Mono patched font and powerline (runs dev_mini). """

    if remote_configuration.is_osx:
        if not exists(sf.tilde('Library/Fonts/UbuntuMono-B-Powerline.ttf')):
            git_clone_or_update('ubuntu-mono-powerline-ttf',
                                'https://github.com/pdf/'
                                'ubuntu-mono-powerline-ttf.git')
            run('cp ubuntu-mono-powerline-ttf/*.ttf %s'
                % sf.tilde('Library/Fonts/UbuntuMono-B-Powerline.ttf'))

    else:
        if not exists(sf.tilde('.fonts/ubuntu-mono-powerline-ttf')):
            run('git clone https://github.com/pdf/ubuntu-mono-powerline-ttf.git'
                ' ~/.fonts/ubuntu-mono-powerline-ttf')
            run('fc-cache -vf')

    git_clone_or_update('powerline-shell',
                        'git@github.com:Karmak23/powerline-shell.git')

# ---------------------------------------------------- Sysadmin recipes


@task
@sf.with_remote_configuration
def test(remote_configuration=None):
    """ Just run `uname -a; uptime` remotely, to test the connection
        or sparks core libs. """

    run('uname -a; uptime; cat /etc/lsb-release || true')


@task
@sf.with_remote_configuration
def sys_easy_sudo(remote_configuration=None):
    """ Allow sudo to run without password for @sudo members. """

    if remote_configuration.is_osx:
        # GNU sed is needed for fabric `sed` command to succeed.
        pkg.brew_add('gnu-sed')
        sf.symlink('/usr/local/bin/gsed', '/usr/local/bin/sed')

        sudoers = '/private/etc/sudoers'
        group   = 'admin'

    else:
        # Debian / Ubuntu
        sudoers = '/etc/sudoers'
        group   = 'sudo'

    with settings(hide('warnings', 'running',
                  'stdout', 'stderr'), warn_only=True):
        sed(sudoers,
            '%%%s\s+ALL\s*=\s*\(ALL(:ALL)?\)\s+ALL' % group,
            '%%%s    ALL = (ALL:ALL) NOPASSWD: ALL' % group,
            use_sudo=True, backup='.bak')


@task
@sf.with_remote_configuration
def sys_unattended(remote_configuration=None):
    """ Install unattended-upgrades and set it up for daily auto-run. """

    if remote_configuration.is_osx:
        info("Skipped unattended-upgrades (not on LSB).")
        return

    pkg.apt_add('unattended-upgrades')

    # always install the files, in case they
    # already exist and have different contents.
    put(os.path.join(os.path.expanduser('~'), 'Dropbox', 'configuration',
        'data', 'uu-periodic.conf'),
        '/etc/apt/apt.conf.d/10periodic', use_sudo=True)
    put(os.path.join(os.path.expanduser('~'), 'Dropbox', 'configuration',
        'data', 'uu-upgrades.conf'),
        '/etc/apt/apt.conf.d/50unattended-upgrades', use_sudo=True)

    # Too long. It will be done by CRON anyway.
    #sudo('unattended-upgrades')


@task
@sf.with_remote_configuration
def sys_del_useless(remote_configuration=None):
    """ Remove useless or annoying packages (LSB only).

        .. note:: cannot remove these, they remove world: ``at-spi2-core``
            ``qt-at-spi``.
    """

    if remote_configuration.is_osx:
        return

    pkg.apt_del(('apport', 'python-apport',
                'landscape-client-ui-install', 'gnome-orca',
                'brltty', 'libbrlapi0.5', 'python3-brlapi', 'python-brlapi',
                'ubuntuone-client', 'ubuntuone-control-panel',
                'rhythmbox-ubuntuone', 'python-ubuntuone-client', 'onboard'))


@task
@sf.with_remote_configuration
def sys_default_services(remote_configuration=None):
    """ Activate some system services I need / use. """

    if remote_configuration.is_osx:
        # Activate locate on OSX.
        sudo('launchctl load -w '
             '/System/Library/LaunchDaemons/com.apple.locate.plist', quiet=True)


@task
@sf.with_remote_configuration
def sys_admin_pkgs(remote_configuration=None):
    """ Install some sysadmin related applications. """

    pkg.pkg_add(('wget', 'multitail', ))

    if not remote_configuration.is_osx:
        pkg.apt_add(('acl', 'attr', 'colordiff', ))


@task
@sf.with_remote_configuration
def sys_ssh_powerline(remote_configuration=None):
    """ Make remote SSHd accept the POWERLINE_SHELL environment variable. """

    git_clone_or_update('powerline-shell',
                        'git@github.com:Karmak23/powerline-shell.git')

    if remote_configuration.is_osx:
        # No need to reload on OSX, cf. http://superuser.com/q/478035/206338
        config     = '/private/etc/sshd_config'
        reload_ssh = None

    else:
        config     = '/etc/ssh/sshd_config'
        reload_ssh = 'reload ssh'

    if not contains(config, 'AcceptEnv POWERLINE_SHELL', use_sudo=True):
        append(config, 'AcceptEnv POWERLINE_SHELL', use_sudo=True)
        if reload_ssh:
            sudo(reload_ssh)


@task(aliases=('lperms', ))
@sf.with_remote_configuration
def local_perms(remote_configuration=None):
    """ Re-apply correct permissions on well-known files (eg .ssh/*) """

    with cd(sf.tilde()):
        local('chmod 700 .ssh; chmod 600 .ssh/*')


@task(aliases=('dupe_perms', 'dupe_acls', 'acls', ))
@sf.with_remote_configuration
def replicate_acls(remote_configuration=None,
                   origin=None, path=None, apply=False):
    """ Replicate locally the ACLs and Unix permissions of a given path.

        This helps correcting strange permissions errors from a well-known
        good machine.

        Usage:

            fabl acls:origin=10.0.3.37,path=/bin
            # Then:
            fabl acls:origin=10.0.3.37,path=/bin,apply=True
    """

    if origin is None or path is None:
        raise ValueError('Missing arguments')

    sys_admin_pkgs()

    local_perms_file  = str(uuid.uuid4())
    remote_perms_file = str(uuid.uuid4())

    with cd('/tmp'):

        # GET correct permissions form origin server.
        with settings(host_string=origin):
            with cd('/tmp'):
                sudo('getfacl -pR "%s" > "%s"' % (path, remote_perms_file))
                get(remote_perms_file, '/tmp')
                sudo('rm "%s"' % remote_perms_file, quiet=True)

        if env.host_string != 'localhost':
            # TODO: find a way to transfer from one server to another directly.
            put(remote_perms_file)

        # gather local permissions, compare them, and reapply
        sudo('getfacl -pR "%s" > "%s"' % (path, local_perms_file))
        sudo('colordiff -U 3 "%s" "%s" || true' % (local_perms_file,
                                                   remote_perms_file))

        sudo('setfacl --restore="%s" %s || true' % (remote_perms_file,
             '' if apply else '--test'))

        sudo('rm "%s" "%s"' % (remote_perms_file, local_perms_file), quiet=True)


# ------------------------------------------------- Development recipes


@sf.with_remote_configuration
def git_clone_or_update(project, github_source, remote_configuration=None):
    """ Clones or update a repository. """

    dev_mini()

    with cd(sf.tilde('sources')):
        if exists(project):
            with cd(project):
                print('Updating GIT repository %s…' % yellow(project))
                run('git up || git pull', quiet=True)
        else:
            print('Creating GIT repository %s…' % yellow(project))
            run('git clone %s %s' % (github_source, project))


@task
@sf.with_remote_configuration
def dev_graphviz(remote_configuration=None):
    """ Graphviz and required packages for PYgraphviz. """

    # graphviz-dev will fail on OSX, but graphiv will install
    # the -dev requisites via brew.
    pkg.pkg_add(('graphviz', 'pkg-config', 'graphviz-dev'))

    pkg.pip2_add(('pygraphviz', ))


@task
@sf.with_remote_configuration
def dev_pil(virtualenv=None, remote_configuration=None):
    """ Required packages to build Python PIL. """

    if remote_configuration.is_osx:
        pilpkgs = ('jpeg', 'libpng', 'libxml2',
                   'freetype', 'libxslt', 'lzlib',
                   'imagemagick')
    else:
        pilpkgs = ('libjpeg-dev', 'libjpeg62', 'libpng12-dev', 'libxml2-dev',
                   'libfreetype6-dev', 'libxslt1-dev', 'zlib1g-dev',
                   'imagemagick')

    pkg.pkg_add(pilpkgs)

    if not remote_configuration.is_osx:
        # Be protective by default, this should be done
        # only in LXC / Virtual machines guests, in order
        # not to pollute the base host system.
        if confirm('Create symlinks in /usr/lib?', default=False):

            with cd('/usr/lib'):
                # TODO: check it works (eg. it suffices
                # to correctly build PIL via PIP).
                for libname in ('libjpeg', 'libfreetype', 'libz'):
                    sf.symlink('/usr/lib/%s-linux-gnu/%s.so'
                               % (remote_configuration.arch, libname),
                               '%s.so' % libname)

            # TODO:     with prefix('workon myvenv'):
            # This must be done in the virtualenv, not system-wide.
            #sudo('pip install -U PIL')

# TODO: rabbitmq-server


@task
@sf.with_remote_configuration
def dev_tildesources(remote_configuration=None):
    """ Create ~/sources if not existing. """

    with cd(sf.tilde()):
        if not exists('sources'):
            if remote_configuration.is_vm:
                if remote_configuration.is_parallel:
                    sf.symlink('/media/psf/Home/sources', 'sources')
            else:
                run('mkdir sources')


@task
@sf.with_remote_configuration
def dev_sqlite(remote_configuration=None):
    """ SQLite development environment (for python packages build). """

    if not remote_configuration.is_osx:
        pkg.pkg_add(('libsqlite3-dev', 'python-all-dev', ))

    pkg.pip2_add(('pysqlite', ))


@task
@sf.with_remote_configuration
def dev_mysql(remote_configuration=None):
    """ MySQL development environment (for python packages build). """

    pkg.pkg_add('' if remote_configuration.is_osx else 'libmysqlclient-dev')


@task
@sf.with_remote_configuration
def dev_postgresql(remote_configuration=None):
    """ PostgreSQL development environment (for python packages build). """

    if not remote_configuration.is_osx:
        pkg.pkg_add(('postgresql-server-dev-9.1', ))

    pkg.pip2_add(('psycopg2', ))


@task
@sf.with_remote_configuration
def dev_mini(remote_configuration=None):
    """ Git and ~/sources/ """

    pkg.pkg_add(('git' if remote_configuration.is_osx else 'git-core'))

    dev_tildesources()


@task
@sf.with_remote_configuration
def dev_web(remote_configuration=None):
    """ Web development packages (NodeJS, Less, Compass…). """

    dev_mini()

    if not remote_configuration.is_osx:
        # Because of http://stackoverflow.com/q/7214474/654755
        sf.ppa('ppa:chris-lea/node.js')

    # NOTE: nodejs` PPA version already includes `npm`,
    # no need to install it via a separate package on Ubuntu.
    pkg.pkg_add(('nodejs', ))

    # But on others, we need.
    if remote_configuration.is_osx:
        pkg.pkg_add(('npm', ))

    sf.npm_add(('less', 'yo',

                # Not yet ready (package throws exceptions on install)
                #'yeoman-bootstrap',

                'bower', 'grunt-cli',
                'generator-angular',
                'coffeescript-compiler', 'coffeescript-concat',
                'coffeescript_compiler_tools'))

    pkg.gem_add(('compass', ))


@task
@sf.with_remote_configuration
def dev(remote_configuration=None):
    """ Generic development (dev_mini + git-flow + Python & Ruby utils). """

    dev_mini()

    if remote_configuration.is_osx:
        # On OSX:
        #    - ruby & gem are already installed.
        #     - via Brew, python will install PIP.
        #     - virtualenv* come only via PIP.
        #    - git-flow-avh brings small typing enhancements.

        pkg.brew_add(('git-flow-avh', 'ack', 'python', ))

    else:
        # On Ubuntu, `ack` is `ack-grep`.
        pkg.apt_add(('git-flow', 'ack-grep', 'python-pip',
                    'ruby', 'ruby-dev', 'rubygems', ))

        # Remove eventually DEB installed old packages (see just after).
        pkg.apt_del(('python-virtualenv', 'virtualenvwrapper', ))

    # Add them from PIP, to have latest
    # version which handles python 3.3 gracefully.
    pkg.pip2_add(('virtualenv', 'virtualenvwrapper', ))

    #TODO: if exists virtualenv and is_lxc(machine):

    # We remove the DEB packages to avoid duplicates and conflicts.
    # It's usually older than the PIP package.
    pkg.pkg_del(('ipython', 'ipython3', ))

    if remote_configuration.is_osx:
        # The brew python3 receipe installs pip3 and development files.
        py3_pkgs = ('python3', )

    else:
        # TODO: 'python3-pip',
        py3_pkgs = ('python3', 'python3-dev', 'python3-examples',
                    'python3-minimal', )

        if int(remote_configuration.lsb.RELEASE.split('.', 1)[0]) > 12:
            py3_pkgs += ('python3.3', 'python3.3-dev', 'python3.3-examples',
                         'python3.3-minimal', )

        pkg.apt_add(('build-essential', 'python-all-dev', ))

    pkg.pkg_add(py3_pkgs)

    pkg.pip2_add(('yolk', 'ipython', 'flake8', ))

    # yolk & flake8 fail because of distribute incompatible with Python 3.
    pkg.pip3_add(('ipython', ))

    # No need yet, it's already available from the system, in Python 2,
    # and can perfectly generate a virtualenv for Python 3.3.
    #pkg.pip3_add(('virtualenv', 'virtualenvwrapper', ))

    pkg.gem_add(('git-up', ))

# --------------------------------------------------- Databases recipes


@task
@sf.with_remote_configuration
def db_sqlite(remote_configuration=None):
    """ SQLite database library. """

    pkg.pkg_add('sqlite' if remote_configuration.is_osx else 'sqlite3')


@task
@sf.with_remote_configuration
def db_mysql(remote_configuration=None):
    """ MySQL database server. """

    pkg.pkg_add('mysql' if remote_configuration.is_osx else 'mysql-server')


@task(aliases=('db_postgres'))
@sf.with_remote_configuration
def db_postgresql(remote_configuration=None):
    """ PostgreSQL database server. """

    if remote_configuration.is_osx:
        if pkg.brew_add(('postgresql', )):
            run('initdb /usr/local/var/postgres -E utf8')
            run('ln -sfv /usr/local/opt/postgresql/*.plist '
                '~/Library/LaunchAgents')
            run('launchctl load ~/Library/LaunchAgents/'
                'homebrew.*.postgresql.plist')

            # Test connection
            # psql template1
    else:
        pkg.apt_add(('postgresql-9.1', ))

    dev_postgresql()

    LOGGER.warning('You still have to tweak pg_hba.conf yourself.')

# -------------------------------------- Server or console applications


@task
@sf.with_remote_configuration
def base(remote_configuration=None):
    """ sys_* + brew (on OSX) + byobu, bash-completion, htop. """

    sys_easy_sudo()

    install_homebrew()

    sys_unattended()
    sys_del_useless()
    sys_default_services()
    sys_admin_pkgs()
    sys_ssh_powerline()

    pkg.pkg_add(('byobu', 'bash-completion',
                'htop-osx' if remote_configuration.is_osx else 'htop'))


@task
@sf.with_remote_configuration
def deployment(remote_configuration=None):
    """ Install Fabric (via PIP for latest paramiko). """

    # We remove the system packages in case they were previously
    # installed, because PIP's versions are more recent.
    # Paramiko <1.8 doesn't handle SSH agent correctly and we need it.
    pkg.pkg_del(('fabric', 'python-paramiko', ))

    pkg.pkg_add(('dsh', ))

    if not remote_configuration.is_osx:
        pkg.pkg_add(('python-all-dev', ))

    pkg.pip2_add(('fabric', ))


@task
@sf.with_remote_configuration
def lxc(remote_configuration=None):
    """ LXC local runner (guests manager). """

    if remote_configuration.is_osx:
        info("Skipped LXC host setup (not on LSB).")
        return

    pkg.apt_add('lxc')

# ------------------------------------ Client or graphical applications

# TODO: rename and refactor these 3 tasks.


@task
@sf.with_remote_configuration
def graphdev(remote_configuration=None):
    """ Graphical applications for the typical development environment.

        .. todo:: clean / refactor contents (OSX mainly).
    """

    pkg.pkg_add(('pdksh', 'zsh', ))

    if remote_configuration.is_osx:
        # TODO: download/install on OSX:
        for app in ('iTerm', 'TotalFinder', 'Google Chrome', 'Airfoil', 'Adium',
                    'iStat Menus', 'LibreOffice', 'Firefox', 'Aperture',
                    'MPlayerX'):
            if not exists('/Applications/%s.app' % app):
                info("Please install %s manually." % yellow(app))
        return

    pkg.apt_add(('gitg', 'meld', 'regexxer', 'cscope', 'exuberant-ctags',
                'vim-gnome', 'terminator', 'gedit-developer-plugins',
                'gedit-plugins', 'geany', 'geany-plugins', ))


@task
@sf.with_remote_configuration
def graphdb(remote_configuration=None):
    """ Graphical and client packages for databases. """

    if remote_configuration.is_osx:
        info("Skipped graphical DB-related packages (not on LSB).")
        return

    pkg.apt_add('pgadmin3')


@task
@sf.with_remote_configuration
def graph(remote_configuration=None):
    """ Poweruser graphical applications. """

    if remote_configuration.is_osx:
        info("Skipped graphical APT packages (not on LSB).")
        return

    if not remote_configuration.lsb.ID.lower() == 'ubuntu':
        info("Skipped graphe PPA packages (not on Ubuntu).")
        return

    pkg.apt_add(('synaptic', 'gdebi', 'compizconfig-settings-manager',
                'dconf-tools', 'gconf-editor', 'pidgin', 'vlc', 'mplayer',
                'indicator-multiload'))

    if remote_configuration.lsb.RELEASE.startswith('13') \
            or remote_configuration.lsb.RELEASE == '12.10':
        sf.ppa_pkg('ppa:freyja-dev/unity-tweak-tool-daily',
                   'unity-tweak-tool', '/usr/bin/unity-tweak-tool')

    elif remote_configuration.lsb.RELEASE == '12.04':
        sf.ppa_pkg('ppa:myunity/ppa', 'myunity', '/usr/bin/myunity')

    sf.ppa_pkg('ppa:tiheum/equinox', ('faience-icon-theme',
               'faenza-icon-theme'), '/usr/share/icons/Faenza')
    sf.ppa_pkg('ppa:caffeine-developers/ppa', 'caffeine', '/usr/bin/caffeine')
    #sf.ppa_pkg('ppa:conscioususer/polly-unstable', 'polly', '/usr/bin/polly')
    sf.ppa_pkg('ppa:kilian/f.lux', 'fluxgui', '/usr/bin/fluxgui')


@task(aliases=('graphkbd', 'kbd', ))
@sf.with_remote_configuration
def graphshortcuts(remote_configuration=None):
    """ Gconf / Dconf keyboard shortcuts for back-from-resume loose. """
    if remote_configuration.is_osx:
        return

    for key, value in (('activate-window-menu', "['<Shift><Alt>space']"),
                       ('toggle-maximized', "['<Alt>space']"), ):

        # Probably less direct than dconf
        #local('gsettings set org.gnome.desktop.wm.keybindings %s "%s"'
        #    % (key, value))

        # doesn't work with 'run()', because X connection is not here.
        local('dconf write /org/gnome/desktop/wm/keybindings/%s "%s"'
              % (key, value))


@task(aliases=('coc', ))
@sf.with_remote_configuration
def clear_osx_cache(remote_configuration=None):
    """ Clears some OSX cache, to avoid opendirectoryd to hog CPU. """

    if not remote_configuration.is_osx:
        return

    # cf. http://support.apple.com/kb/HT3540
    # from http://apple.stackexchange.com/q/33312
    # because opendirectoryd takes 100% CPU on my MBPr.
    run('dscl . -list Computers | grep -v "^localhost$" '
        '| while read computer_name ; do sudo dscl . -delete '
        'Computers/"$computer_name" ; done', quiet=True)


@task
@sf.with_remote_configuration
def upload_osx_apps(remote_configuration=None):
    """ Upload local OSX Apps to my central location for easy redistribution
        without harvesting the internet on every new machine.

        .. note:: there is currently no “ clean outdated files ” procedure…
    """

    run('mkdir -p %s' % central_osx_apps.split(':')[1], quiet=True)
    run('rsync -av %s %s' % (local_osx_apps, central_osx_apps))

# =========================================== My personnal environments


@task
@sf.with_remote_configuration
def myapps(remote_configuration=None):
    """ Skype + Chrome + Sublime + 1Password """

    install_skype()
    install_chrome()
    install_sublime()

    if not remote_configuration.is_vm:
        # No need to pollute the VM with wine,
        # I already have 1Password installed under OSX.
        install_1password()


@task
@sf.with_remote_configuration
def mydevenv(remote_configuration=None):
    """ Clone my professional / personnal projects with GIT in ~/sources """

    install_powerline()

    dev()
    dev_web()

    deployment()

    # NO clone, it's already in my dropbox!
    #git_clone_or_update('sparks', 'git@github.com:Karmak23/sparks.git')
    #
    # Just symlink it to my sources for centralization/normalization
    # purposes. Or is it just bad-habits? ;-)
    with cd(sf.tilde('sources')):
        sf.symlink('../Dropbox/sparks', 'sparks')

    git_clone_or_update('pelican-themes',
                        'git@github.com:Karmak23/pelican-themes.git')

    # Not yet ready
    #git_clone_or_update('1flow', 'dev.1flow.net:/home/groups/oneflow.git')

    git_clone_or_update('licorn', 'dev.licorn.org:/home/groups/licorn.git')
    git_clone_or_update('mylicorn', 'my.licorn.org:/home/groups/mylicorn.git')


@task
@sf.with_remote_configuration
def mydotfiles(overwrite=False, locally=False, remote_configuration=None):
    """ Symlink a bunch of things to Dropbox/… """

    with cd(sf.tilde()):

        sf.symlink('Dropbox/bin', 'bin', overwrite=overwrite, locally=locally)
        sf.symlink('Dropbox/configuration/virtualenvs', '.virtualenvs',
                   overwrite=overwrite, locally=locally)

        for filename in ('dsh', 'ssh', 'ackrc', 'bashrc', 'fabricrc',
                         'gitconfig', 'gitignore', 'dupload.conf',
                         'multitailrc'):
            sf.symlink(sf.dotfiles('dot.%s' % filename),
                       '.%s' % filename, overwrite=overwrite, locally=locally)

        if not remote_configuration.is_osx:
            if not exists('.config'):
                local('mkdir .config') if locally else run('mkdir .config')

            with cd('.config'):
                # These don't handle the Dropboxed configuration / data
                # correctly. We won't symlink their data automatically.
                symlink_blacklist = ('caffeine', )

                base_path   = sf.tilde(sf.dotfiles('dot.config'))
                ln_src_path = os.path.join('..', base_path)

                # NOTE: this lists files on the local
                # host, not the remote target.
                for entry in os.listdir(base_path):
                    if entry.startswith('.'):
                        continue

                    if entry in symlink_blacklist:
                        if not exists(entry):
                            print("Please copy %s to ~/.config/ yourself."
                                  % os.path.join(ln_src_path, entry))
                        continue

                    # But this will do the symlink remotely.
                    sf.symlink(os.path.join(ln_src_path, entry), entry,
                               overwrite=overwrite, locally=locally)


@task(aliases=('myenv', ))
@sf.with_remote_configuration
def myfullenv(remote_configuration=None):
    """ sudo + full + fullgraph + mydev + mypkg + mydot """

    base()

    graphdev()
    graphdb()
    graph()

    mydotfiles()
    myapps()
    mydevenv()

    # ask questions last, when everything else has been installed / setup.
    if not remote_configuration.is_osx and confirm(
                'Reinstall bcmwl-kernel-source (MacbookAir(3,2) late 2010)?',
                default=False):
        # Reinstall / rebuild the BCM wlan driver.
        # NM should detect and re-connect automatically at the end.
        sudo('apt-get install --reinstall bcmwl-kernel-source')


@task(aliases=('mysetup', ))
@sf.with_remote_configuration
def mybootstrap(remote_configuration=None):
    """ Bootstrap my personal environment on the local machine. """

    pkg.apt_add(('ssh', ), locally=True)

    mydotfiles(remote_configuration=None, locally=True)

# ============================================= LXC guests environments


@task
@sf.with_remote_configuration
def lxc_base(remote_configuration=None):
    """ Base packages for an LXC guest (base+LANG+dev). """

    if remote_configuration.is_osx:
        info('Skipped lxc_base (not on LSB).')
        return

    base()

    pkg.apt_update()

    # install the locale before everything, else DPKG borks.
    pkg.apt_add(('language-pack-fr', 'language-pack-en', ))

    # Remove firefox's locale, it's completely sys_del_useless in a LXC.
    pkg.apt_del(('firefox-locale-fr', 'firefox-locale-en', ))

    # TODO: nullmailer, bsd-mailx… Cf. my LXC documentation.

    # install a dev env.
    dev()


@task
@sf.with_remote_configuration
def lxc_server(remote_configuration=None):
    """ LXC base + server packages (Pg). """

    lxc_base()
    db_postgresql()
