# Sparks

My *foundations* repository, which I use to bootstrap any new project or machine. Written in `Python`.

- Uses [Fabric](http://fabfile.org/) to deploy.
- Can deploy many machines at a time (eg `fab -R lxc-group lxc_base -P -z 10` works as expected).
- Works on Ubuntu and OSX *hosts* and *targets*, even mixed (I use both, daily).
- Is implemented with a lot of tasks and subtasks, which can be re-used to your liking (see `fab --list`).
- Includes a unified package search tool (`utils/pkgmgr.py`, see below).
- Contains some modules and a dedicated `fabfile` for bootstraping `Django` projects very quickly. It still needs a little love on the sysadmin side, because installation of system dependancies like PostgreSQL or redis/memcache must be handled manually (there's a start in the `fabfile`, but it's inactive for now).

In the near future:
- it will likely contain some `AngularJS` modules, too.

## List of fabric tasks


### Machine installation-related

You can get an up-to-date list with `fab --list`. Some of them have *aliases*, which I didn't display here.

    base                  sys_* + brew (on OSX) + byobu, bash-completion, htop.
    clear_osx_cache       Clears some OSX cache, to avoid opendirectoryd to hog CPU.
    db_mysql              MySQL database server.
    db_postgres           PostgreSQL database server.
    db_sqlite             SQLite database library.
    deployment            Install Fabric (via PIP for latest paramiko).
    dev                   Generic development (dev_mini + git-flow + Python & Ruby utils).
    dev_graphviz          Graphviz and required packages for PYgraphviz.
    dev_mini              Git and ~/sources/
    dev_mysql             MySQL development environment (for python packages build).
    dev_pil               Required packages to build Python PIL.
    dev_sqlite            SQLite development environment (for python packages build).
    dev_tildesources      Create ~/sources if not existing.
    dev_web               Web development packages (NodeJS, Less, Compass…).
    graph                 Poweruser graphical applications.
    graphdb               Graphical and client packages for databases.
    graphdev              Graphical applications for the typical development environment.
    graphkbd              Gconf / Dconf keyboard shortcuts for back-from-resume loose.
    local_perms           Re-apply correct permissions on well-known files (eg .ssh/*)
    lxc                   LXC local runner (guests manager).
    lxc_base              Base packages for an LXC guest (base+LANG+dev).
    lxc_server            LXC base + server packages (Pg).
    myapps                Skype + Chrome + Sublime + 1Password
    mybootstrap           Bootstrap my personal environment on the local machine.
    mydevenv              Clone my professional / personnal projects with GIT in ~/sources
    mydotfiles            Symlink a bunch of things to Dropbox/…
    myenv                 sudo + full + fullgraph + mydev + mypkg + mydot
    myfullenv             sudo + full + fullgraph + mydev + mypkg + mydot
    mysetup               Bootstrap my personal environment on the local machine.
    sys_admin_pkgs        Install some sysadmin related applications.
    sys_default_services  Activate some system services I need / use.
    sys_del_useless       Remove useless or annoying packages (LSB only).
    sys_easy_sudo         Allow sudo to run without password for @sudo members.
    sys_ssh_powerline     Make remote SSHd accept the POWERLINE_SHELL environment variable.
    sys_unattended        Install unattended-upgrades and set it up for daily auto-run.
    test                  Just run `uname -a; uptime` remotely, to test the connection
    sf.update             Refresh all package management tools data (packages lists, receipes…).
    sf.upgrade            Upgrade all outdated packages from all pkg management tools at once.

### Django-related tasks

You **must** create your own `fabfile` in your project, and import the sparks one. You just have to specify `env` configuration, and the sparks `fabfile` will do the rest, providing commonly used targets, named `initial`, `deploy` and so on. Considering the `fabfile`:

    import os
    from fabric.api import env, task
    import sparks.django.fabfile as sdf
    from oneflow import settings as oneflow_settings

    # handy aliases for lazy typing…
    runable = sdf.runable
    deploy  = sdf.deploy

    env.project    = '1flow'
    env.virtualenv = '1flow'
    env.user       = '1flow'
    env.settings   = oneflow_settings
    env.root       = '/home/1flow/www'

    @task
    def local():
        env.host_string = 'localhost'
        env.user        = 'olive'
        env.environment = 'test'
        env.root        = os.path.expanduser('~/sources/1flow')

    @task
    def test():
        env.host_string = 'obi.1flow.net'
        env.environment = 'test'

    @task
    def production():
        env.host_string = '1flow.net'
        env.environment = 'production'


Here is the resulting tasks list, with aliases removed for clarity:

    local                   >
    production              > My 3 targets.
    test                    >
    deploy                  Pull code, ensure runable, restart services.
    runable                 Ensure we can run the {web,dev}server: db+req+sync+migrate+static.
    sdf.collectstatic       Run the Django collectstatic management command.
    sdf.createdb            Create the PostgreSQL user & database. It's OK if already existing.
    sdf.migrate             Run the Django migrate management command.
    sdf.requirements        Install PIP requirements (and dev-requirements).
    sdf.restart_celery      Restart celery (only if detected as installed).
    sdf.restart_supervisor  (Re-)upload configuration files and reload gunicorn via supervisor.
    sdf.syncdb              Run the Django syndb management command.

#### Assumptions & conventions

The Django sparks `fabfile` includes a little conventions-related magic:

- it will include your Django `settings` and use `.DEBUG` and `.DATABASES` values.
- if your local machine runs OSX, it will assume you are in test mode (I develop on OSX and run production code on Linux servers).
- when doing remote deployments, you have to set fabric's `env.environment` to either `test` or `production`.


## Installation How-to

On OSX, you will have a chicken-and-egg problem because `git` is not installed by default. I personally solves this by installing `Dropbox` first, which contains an up-to-date copy of this `sparks` repository, and the `1nstall.py` scripts takes care of the rest (see below).

On Ubuntu, just `sudo apt-get install git-core` and you're ready to shine (see below too).

NOTE: In my Dropbox I have private data or configuration files, which are highly personal (some contains passwords or hashes). You may see a small number of fabric targets crash because of these missing files. Perhaps you should just study them and customize them to your likings before using this library.

### First installation on a brand new machine

This is what I run on a virgin machine to get everything up and running:

- install Dropbox and let it sync
- on OSX, install Xcode and CLI Tools for Xcode
- then:

	~Dropbox/sparks/1nstall.py

- wait for the command to complete, download and install everything,
- enjoy my new machine with all my environment and software, ready to go.

You can do the same without `Dropbox`, with:

	git clone https://github.com/Karmak23/sparks
	./sparks/1nstall.py

`1nstall` will:

- On OSX, install `Brew`, an up-to-date `Python`, and `git`.
- On Ubuntu and OSX, install all of my needed software to be fully operational.


### Simple package manager

It's a command-line utility, which handles `brew` on OSX, `apt-*` on `Ubuntu` / `Debian`, `npm`, `pip` and `gem`.

#### Installation

	ln -sf path/to/sparks/utils/pkgmrg.py ~/bin/search

#### Usage

	# search for a package, globaly, everywhere:
	search toto

As of now, only `search` is implemented. `install`, `remove` and other are planned, but would be only aliases to underlying tools and are thus not that useful. I currently have shell aliases pointing to `brew` or `apt-*`, given the OS I’m on, and that’s quite satisfying.


## Example with powerline

`powerline-shell` is not that useful, but the whole example is complex, and thus a good thing to show you how I use `sparks`.

In `~/.ssh/config` (stored in `Dropbox`), I have:

	Host *
		SendEnv POWERLINE_SHELL

In `~/.bashrc` (stored in `Dropbox`), I have:

	if [ \( \
			\( -e ~/.fonts/ubuntu-mono-powerline-ttf \
			-o -e ~/Library/Fonts/UbuntuMono-B-Powerline.ttf \) \
			-o \
			\( -n "$SSH_CLIENT" -a -n "POWERLINE_SHELL" \) \
		\)\
		-a -e ~/sources/powerline-shell ]; then

		# Use the fancy powerline
		function _update_ps1() {
		   export PS1="$(~/sources/powerline-shell/powerline-shell.py $?)"
		}

		export POWERLINE_SHELL=true
		export PROMPT_COMMAND="_update_ps1"

	else
		# normal prompt, without powerline installed…

	fi

Then, i run:

	fab -R lxc-hosts -P -z 5 sys_ssh_powerline

Which will clone the powerline GIT repository in the remote machines and configure their SSHds to accept the local exported variable. With that setup, I don't need to run the full `install_powerline` target on them, so they don't get the powerline font installed (which is useless on a remote headless server).

And after that, I can enjoy powerline everywhere, but the font is only installed on my laptop or PC.
