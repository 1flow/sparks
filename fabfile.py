# -*- coding: utf8 -*-

import os
import sys

from fabric.api              import env, run, sudo, local, task
from fabric.operations       import put
from fabric.contrib.console  import confirm
from fabric.contrib.files    import append, exists, sed
from fabric.context_managers import cd, settings, hide
from fabric.colors           import yellow, cyan

if __package__ is None:
    # See #2 comment of http://stackoverflow.com/a/11537218/654755
    # and http://www.python.org/dev/peps/pep-0366/
    sys.path.append(os.path.expanduser('~/Dropbox'))

from sparks import fabric as sf

# ================================================ Fabric configuration

env.use_ssh_config = True
env.roledefs       = sf.dsh_to_roledefs()

is_osx = sf.lsb is None


def info(text):
    print(cyan(text))

# ====================================================== Fabric targets

# -------------------------------------- Standalone application recipes


def install_chrome():
    """ Install Google Chrome via .DEB packages from Google. """

    if is_osx:
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
        sf.apt_update()
        sf.apt_add('google-chrome-stable')


def install_skype():
    """ Install Skype 32bit via Ubuntu partner repository. """

    if is_osx:
        if not exists('/Applications/Skype.app'):
            # TODO: implement me.
            info("Please install %s manually." % yellow('Skype'))

    else:
        sf.ppa_pkg('deb http://archive.canonical.com/ubuntu %s partner'
                   % sf.lsb.CODENAME, 'skype', '/usr/bin/skype')


def install_sublime(overwrite=False):
    """ Install Sublime Text 2 in /opt via a downloaded .tar.bz2. """

    if is_osx:
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


def install_homebrew():
    """ Install Homebrew on OSX from http://mxcl.github.com/homebrew/ """

    if not is_osx:
        return

    if exists('/usr/local/bin/brew'):

        if confirm('Update Brew Formulæ?', default=False):
            sf.brew_update()

        if confirm('Upgrade outdated Brew packages?',
                   default=False):
            sf.brew_upgrade()

    else:
        sudo('ruby -e "$(curl -fsSL https://raw.github.com/mxcl/homebrew/go)"')
        sudo('brew doctor')

        # TODO: implement this.
        info('Please install OSX CLI tools for Xcode manually.')

        if confirm('Is the installation OK?'):
            sf.brew_update()


def install_1password():
    """ NOT IMPLEMENTED: Install 1Password. """

    if is_osx:
        if not exists('/Applications/1Password.app'):
            info('Please install %s manually.' % yellow('1Password'))

    else:
        # TODO: implement me
        sf.apt_add('wine')


def install_powerline():
    """ Install the Ubuntu Mono patched font and powerline (runs dev_mini). """

    if is_osx:
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
def sys_easy_sudo():
    """ Allow sudo to run without password for @sudo members. """

    if is_osx:
        # GNU sed is needed for fabric `sed` command to succeed.
        sf.brew_add('gnu-sed')
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
def sys_unattended():
    """ Install unattended-upgrades and set it up for daily auto-run. """

    if is_osx:
        info("Skipped unattended-upgrades (not on LSB).")
        return

    sf.apt_add('unattended-upgrades')

    # always install the files, in case they
    # already exist and have different contents.
    put(os.path.join('Dropbox', 'configuration', 'data', 'uu-periodic.conf'),
        '/etc/apt/apt.conf.d/10periodic', use_sudo=True)
    put(os.path.join('Dropbox', 'configuration', 'data', 'uu-upgrades.conf'),
        '/etc/apt/apt.conf.d/50unattended-upgrades', use_sudo=True)

    # Too long. It will be done by CRON anyway.
    #sudo('unattended-upgrades')


@task
def sys_del_useless():
    """ Remove useless or annoying packages (LSB only).

        .. note:: cannot remove these, they remove world: ``at-spi2-core``
            ``qt-at-spi``.
    """

    if is_osx:
        return

    sf.apt_del(('apport', 'python-apport',
                'landscape-client-ui-install', 'gnome-orca',
                'brltty', 'libbrlapi0.5', 'python3-brlapi', 'python-brlapi',
                'ubuntuone-client', 'ubuntuone-control-panel',
                'rhythmbox-ubuntuone', 'python-ubuntuone-client', 'onboard'))


@task
def sys_default_services():
    """ Activate some system services I need / use. """

    if is_osx:
        # Activate locate on OSX.
        sudo('launchctl load -w '
             '/System/Library/LaunchDaemons/com.apple.locate.plist', quiet=True)


@task
def sys_admin_pkgs():
    """ Install some sysadmin related applications. """

    sf.pkg_add(('wget', 'multitail', ))


@task(aliases=('lperms', ))
def local_perms():
    with cd(sf.tilde()):
        local('chmod 700 .ssh; chmod 600 .ssh/*')


# ------------------------------------------------- Development recipes


def git_clone_or_update(project, github_source):
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
def dev_graphviz():
    """ Graphviz and required packages for PYgraphviz. """

    # graphviz-dev will fail on OSX, but graphiv will install
    # the -dev requisites via brew.
    sf.pkg_add(('graphviz', 'pkg-config', 'graphviz-dev'))

    sf.pip_add(('pygraphviz', ))


@task
def dev_pil(virtualenv=None):
    """ Required packages to build Python PIL. """

    if is_osx:
        pilpkgs = ('jpeg', 'libpng', 'libxml2',
                   'freetype', 'libxslt', 'lzlib',
                   'imagemagick')
    else:
        pilpkgs = ('libjpeg-dev', 'libjpeg62', 'libpng12-dev', 'libxml2-dev',
                   'libfreetype6-dev', 'libxslt1-dev', 'zlib1g-dev',
                   'imagemagick')

    sf.pkg_add(pilpkgs)

    if not is_osx:
        # Be protective by default, this should be done
        # only in LXC / Virtual machines guests, in order
        # not to pollute the base host system.
        if confirm('Create symlinks in /usr/lib?', default=False):

            arch = sf.uname.machine

            with cd('/usr/lib'):
                # TODO: check it works (eg. it suffices
                # to correctly build PIL via PIP).
                for libname in ('libjpeg', 'libfreetype', 'libz'):
                    sf.symlink('/usr/lib/%s-linux-gnu/%s.so'
                               % (arch, libname), '%s.so' % libname)

            # TODO:     with prefix('workon myvenv'):
            # This must be done in the virtualenv, not system-wide.
            #sudo('pip install -U PIL')

# TODO: rabbitmq-server


@task
def dev_tildesources():
    """ Create ~/sources if not existing. """

    with cd(sf.tilde()):
        if not exists('sources'):
            if sf.is_vm:
                if sf.is_parallel:
                    sf.symlink('/media/psf/Home/sources', 'sources')
            else:
                run('mkdir sources')


@task
def dev_mysql():
    """ MySQL development environment (for python packages build). """

    sf.pkg_add('' if is_osx else 'libmysqlclient-dev')


@task
def dev_sqlite():
    """ SQLite development environment (for python packages build). """

    if not is_osx:
        sf.pkg_add(('libsqlite3-dev', 'python-all-dev', ))

    sf.pip_add(('pysqlite', ))


@task
def dev_mini():
    """ Git and ~/sources/ """

    sf.pkg_add(('git' if is_osx else 'git-core'))

    dev_tildesources()


@task
def dev_web():
    """ Web development packages (NodeJS, Less, Compass…). """

    dev_mini()

    if not is_osx:
        # Because of http://stackoverflow.com/q/7214474/654755
        sf.ppa('ppa:chris-lea/node.js')

    # NOTE: nodejs` PPA version already includes `npm`,
    # no need to install it via a separate package on Ubuntu.
    sf.pkg_add(('nodejs', ))

    # But on others, we need.
    if is_osx:
        sf.pkg_add(('npm', ))

    sf.npm_add(('less', 'yo',

                # Not yet ready (package throws exceptions on install)
                #'yeoman-bootstrap',

                'bower', 'grunt-cli',
                'generator-angular',
                'coffeescript-compiler', 'coffeescript-concat',
                'coffeescript_compiler_tools'))

    sf.gem_add(('compass', ))


@task
def dev():
    """ Generic development (dev_mini + git-flow + Python & Ruby utils). """

    dev_mini()

    if is_osx:
        # On OSX:
        #    - ruby & gem are already installed.
        #     - via Brew, python will install PIP.
        #     - virtualenv* come only via PIP.
        #    - git-flow-avh brings small typing enhancements.

        sf.brew_add(('git-flow-avh', 'ack', 'python', ))
        sf.pip_add(('virtualenv', 'virtualenvwrapper', ))

    else:
        # On Ubuntu, `ack` is `ack-grep`.
        sf.apt_add(('git-flow', 'ack-grep', 'python-pip',
                    'python-virtualenv', 'virtualenvwrapper',
                    'ruby', 'ruby-dev', 'rubygems', ))

    #TODO: if exists virtualenv and is_lxc(machine):

    # We remove the DEB packages to avoid duplicates and conflicts.
    sf.pkg_del(('ipython', ))

    sf.pip_add(('yolk', 'ipython', 'flake8', 'pylint', ))

    sf.gem_add(('git-up', ))

# --------------------------------------------------- Databases recipes


@task
def db_sqlite():
    """ SQLite database library. """

    sf.pkg_add('sqlite' if is_osx else 'sqlite3')


@task
def db_mysql():
    """ MySQL database server. """

    sf.pkg_add('mysql' if is_osx else 'mysql-server')


@task
def db_postgres():
    """ PostgreSQL database server. """

    sf.pkg_add('postgresql' if is_osx else 'postgresql-9.1')


# -------------------------------------- Server or console applications


@task
def base():
    """ sys_* + brew (on OSX) + byobu, bash-completion, htop. """

    sys_easy_sudo()
    sys_unattended()
    sys_del_useless()
    sys_default_services()
    sys_admin_pkgs()

    install_homebrew()

    sf.pkg_add(('byobu', 'bash-completion',
                'htop-osx' if is_osx else 'htop'))


@task
def deployment():
    """ Install Fabric (via PIP for latest paramiko). """

    # We remove the system packages in case they were previously
    # installed, because PIP's versions are more recent.
    # Paramiko <1.8 doesn't handle SSH agent correctly and we need it.
    sf.pkg_del(('fabric', 'python-paramiko', ))

    sf.pkg_add(('dsh', ))
    sf.pip_add(('fabric', ))


@task
def lxc():
    """ LXC local runner (guests manager). """

    if is_osx:
        info("Skipped LXC host setup (not on LSB).")
        return

    sf.apt_add('lxc')

# ------------------------------------ Client or graphical applications

# TODO: rename and refactor these 3 tasks.


@task
def graphdev():
    """ Graphical applications for the typical development environment.

        .. todo:: clean / refactor contents (OSX mainly).
    """

    sf.pkg_add(('pdksh', 'zsh', ))

    if is_osx:
        # TODO: download/install on OSX:
        for app in ('iTerm', 'TotalFinder', 'Google Chrome', 'Airfoil', 'Adium',
                    'iStat Menus', 'LibreOffice', 'Firefox', 'Aperture',
                    'MPlayerX'):
            if not exists('/Applications/%s.app' % app):
                info("Please install %s manually." % yellow(app))
        return

    sf.apt_add(('gitg', 'meld', 'regexxer', 'cscope', 'exuberant-ctags',
                'vim-gnome', 'terminator', 'gedit-developer-plugins',
                'gedit-plugins', 'geany', 'geany-plugins', ))


@task
def graphdb():
    """ Graphical and client packages for databases. """

    if is_osx:
        info("Skipped graphical DB-related packages (not on LSB).")
        return

    sf.apt_add('pgadmin3')


@task
def graph():
    """ Poweruser graphical applications. """

    if is_osx:
        info("Skipped graphical APT packages (not on LSB).")
        return

    if not sf.lsb.ID.lower() == 'ubuntu':
        info("Skipped graphe PPA packages (not on Ubuntu).")
        return

    sf.apt_add(('synaptic', 'gdebi', 'compizconfig-settings-manager',
                'dconf-tools', 'gconf-editor', 'pidgin', 'vlc', 'mplayer',
                'indicator-multiload'))

    if sf.lsb.RELEASE.startswith('13') or sf.lsb.RELEASE == '12.10':
        sf.ppa_pkg('ppa:freyja-dev/unity-tweak-tool-daily',
                   'unity-tweak-tool', '/usr/bin/unity-tweak-tool')

    elif sf.lsb.RELEASE == '12.04':
        sf.ppa_pkg('ppa:myunity/ppa', 'myunity', '/usr/bin/myunity')

    sf.ppa_pkg('ppa:tiheum/equinox', ('faience-icon-theme',
               'faenza-icon-theme'), '/usr/share/icons/Faenza')
    sf.ppa_pkg('ppa:caffeine-developers/ppa', 'caffeine', '/usr/bin/caffeine')
    #sf.ppa_pkg('ppa:conscioususer/polly-unstable', 'polly', '/usr/bin/polly')
    sf.ppa_pkg('ppa:kilian/f.lux', 'fluxgui', '/usr/bin/fluxgui')


@task(aliases=('graphkbd', 'kbd', ))
def graphshortcuts():
    """ Gconf / Dconf keyboard shortcuts for back-from-resume loose. """
    if not sf.lsb:
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
def clear_osx_cache():
    if not is_osx:
        return

    # cf. http://support.apple.com/kb/HT3540
    # from http://apple.stackexchange.com/q/33312
    # because opendirectoryd takes 100% CPU on my MBPr.
    run('dscl . -list Computers | grep -v "^localhost$" '
        '| while read computer_name ; do sudo dscl . -delete '
        'Computers/"$computer_name" ; done', quiet=True)


# =========================================== My personnal environments


@task
def myapps():
    """ Skype + Chrome + Sublime + 1Password """

    install_skype()
    install_chrome()
    install_sublime()

    if not sf.is_vm:
        # No need to pollute the VM with wine,
        # I already have 1Password installed under OSX.
        install_1password()


@task
def mydevenv():
    """ Clone my professional / personnal projects with GIT in ~/sources """

    install_powerline()

    dev()
    dev_web()

    deployment()

    # NO clone, it's already in my dropbox!
    #git_clone_or_update('sparks', 'git@github.com:Karmak23/sparks.git')

    # Just symlink it to my sources for centralization/normalization
    # purposes. Or is it just bad-habits? ;-)
    with cd(sf.tilde('sources')):
        sf.symlink('../Dropbox/sparks', 'sparks')

    # Not yet ready
    #git_clone_or_update('1flow', 'dev.1flow.net:/home/groups/oneflow.git')

    git_clone_or_update('licorn', 'dev.licorn.org:/home/groups/licorn.git')
    git_clone_or_update('mylicorn', 'my.licorn.org:/home/groups/mylicorn.git')


@task
def mydotfiles(overwrite=False, locally=False):
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

        if not is_osx:
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
def myfullenv():
    """ sudo + full + fullgraph + mydev + mypkg + mydot """

    base()

    graphdev()
    graphdb()
    graph()

    mydotfiles()
    myapps()
    mydevenv()

    # ask questions last, when everything else has been installed / setup.
    if not is_osx and confirm(
                'Reinstall bcmwl-kernel-source (MacbookAir(3,2) late 2010)?',
                default=False):
        # Reinstall / rebuild the BCM wlan driver.
        # NM should detect and re-connect automatically at the end.
        sudo('apt-get install --reinstall bcmwl-kernel-source')


@task(aliases=('mysetup', ))
def mybootstrap():
    """ Bootstrap my personal environment on the local machine. """

    sf.apt_add(('ssh', ), locally=True)

    mydotfiles(locally=True)

# ============================================= LXC guests environments


@task
def lxc_base():
    """ Base packages for an LXC guest (base+LANG+dev). """

    if is_osx:
        info('Skipped lxc_base (not on LSB).')
        return

    base()

    sf.apt_update()

    # install the locale before everything, else DPKG borks.
    sf.apt_add(('language-pack-fr', 'language-pack-en', ))

    # Remove firefox's locale, it's completely sys_del_useless in a LXC.
    sf.apt_del(('firefox-locale-fr', 'firefox-locale-en', ))

    # TODO: unattended-upgrades, nullmailer

    # install a dev env.
    dev()


@task
def lxc_server():
    """ LXC base + server packages (Pg). """

    lxc_base()
    db_postgres()
    #TODO: pgdev()
