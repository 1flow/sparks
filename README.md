# Sparks

This is my *foundations* deployment tool and receipes. I use to bootstrap any new project or machine. It's written in `Python`. Features and advantages:

- provides a handful set of `Fabric` rules, notably for complex Django projects (celery, redis, memcache, mongodb+mongoengine…).
- allows far more flexibility to `Fabric` behavior. Eg. the chain of execution is no more fixed, you can easily deploy a new machine, without touching existing ones (see note).

- Can deploy many machines at a time (eg `fab -R lxc-group lxc_base -P -z 10` works as expected).
- Works on Ubuntu and OSX *hosts* and *targets*, even mixed (I use both, daily).
- Is implemented with a lot of tasks and subtasks, which can be re-used to your liking (see `fab --list`).
- Includes a unified package search tool (`utils/pkgmgr.py`, see below).
- Contains some modules and a dedicated `fabfile` for bootstraping `Django` projects very quickly. It still needs a little love on the sysadmin side, because installation of system dependancies like PostgreSQL or redis/memcache must be handled manually (there's a start in the `fabfile`, but it's inactive for now).

## Flexible execution model

This is a sparks addition to the `Fabric` model. It gives us the ability to deploy one machine without touching others. 

This approach is usually considered harmful, because it can lead to desynchronization between the new machine and those which aren't hit by the current execution. Generally speaking, I agree with this. But in a constant scaling scenario where we regularly deploy new machines, this is a pain in the ass.

There are 2 points here:

- the developer (or “source-code”) standpoint, where every machine must be exactly in sync everytime. This points backs the current `Fabric` execution model, and must stay the default.
- the sysadmin-only standpoint, where I want to be able to deploy a new machine without touching or even restarting the running ones. Eg. I want to be able to quickly add a celery node without restarting the webserver. Considering “only-stable-releases”, this features allows faster deployments.

It's thus your responsibility to use the sparks models, which assumes you know what you are doing. If not sure, use the classic Fabric model, which is safer but redo a lot of useless work in some specific conditions.


## Most useful tasks

I will not list them all here, there are too much and it's beyond the scope of a README. You can get an up-to-date list with `fab --list`. A lot have *aliases*, which don't show here.

### Metal-installation-related

    test                  Run base commands to test the connection and local user profile.
    base                  sys_* + brew (on OSX) + byobu, bash-completion, htop…

    lxc                   LXC host (guests manager).
    lxc_base              Base packages for an LXC guest (base+LANG+dev).
    lxc_server            LXC base + server packages (Pg).

    db_postgres           PostgreSQL database server.
    db_redis              Redis server. Uses the PPA for latest stable package on Ubuntu.
    db_mongodb            MongoDB server. Uses PPA for same benefits.

    deployment            Installs Fabric (via PIP for latest paramiko).

### Sysadmin-related

    sys_admin_pkgs        Install some sysadmin related applications.
    sys_easy_sudo         Allow sudo to run without password for @sudo members.
    sys_unattended        Install unattended-upgrades and set it up for daily auto-run.
    sf.update             Refresh all package management data (packages lists, receipes…).
    sf.upgrade            Upgrade all outdated packages from all managements tools at once.


### Development-related

    dev_mini              Git and ~/sources/
    dev                   Generic development (dev_mini + git-flow + Python & Ruby utils).
    dev_web               Web development packages (NodeJS, Less, Compass…).

    local_perms           Re-apply correct permissions on well-known files (eg .ssh/*)


### Django-related

Important: **you must create your own `fabfile`** in your project and import the `sparks` one. You just have to specify `env` configuration, and the sparks `fabfile` will do the rest, providing commonly used targets, named `initial`, `deploy` and so on. Minimal example:

    # See https://github.com/1flow/1flow/ for fully-featured and always-up-to-date file.
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
        env.host_string = 'obi.1flow.io'
        env.environment = 'test'

    @task
    def production():
        env.host_string = '1flow.io'
        env.environment = 'production'


Here is the resulting tasks list, with aliases removed for clarity:

    local                   >
    production              > The 3 "machines" targets.
    test                    >
    deploy                  Pull code, ensure runable, restart services.
    runable                 Ensure we can run the {web,dev}server: db+req+sync+migrate+static.

Some sparks subtasks, always runable one-by-one:

    sdf.requirements        Install PIP requirements (and dev-requirements).
    sdf.createdb            Create the DB user & database. It's OK if already existing.
    sdf.syncdb              Run the Django syndb management command.
    sdf.migrate             Run the Django migrate management command.
    sdf.collectstatic       Run the Django collectstatic management command.
    sdf.restart             Restart all running services
    sdf.restart_*           Restart only some services (eg. celery, µwsgi…).


### Assumptions & conventions

The Django sparks `fabfile` includes a little conventions-related magic:

- it will include your Django `settings` and use `.DEBUG` and `.DATABASES` values.
- when acting remotely, **Django settings will be the remote ones**. This is a major feature: settings are reloaded after source-code pull. This implies settings can be different from one machine to another if you use the sparks hostname-based settings mechanism or any other that is “Django compatible” (eg. which make `from django.conf import settings` working as usual).
- if your local machine runs OSX, it will assume you are in test mode (I don't support OSX as servers, only Linux ones; if you don't agree, please submit a patch).
- when doing remote deployments, you have to set fabric's `env.environment` to either `test` or `production`.


## Installation How-to


### OSX note

On OSX, you will have a chicken-and-egg problem because `git` is not installed by default. You will thus need to install `Xcode` and `CLI Tools for Xcode`, then `brew` and `git`. I personally solves this by installing `Dropbox` first, which contains an up-to-date copy of this `sparks` repository, and the `1nstall.py` scripts takes care of most of the rest (see below).

### Ubuntu-like installation

On Ubuntu, if `git` is not installed by default (did you remove it??), just `sudo apt-get install git-core` and you're ready to roll out.

NOTE: A small number of task can crash because of missing files. They depend on private configuration files that exist only in my Dropbox. Sorry for that. I will probably externalize these tasks outside of `sparks` for clarity in the future.


### First installation on a brand new machine

This is what I run on a virgin machine to get everything up and running:

- install `Dropbox` and let it sync
- on OSX, install `Xcode` and `CLI Tools for Xcode`
- then:

	~Dropbox/sparks/1nstall.py

- wait for the command to complete, download and install everything,
- enjoy my new machine with all my environment and software, ready to go.

You can do the same without `Dropbox`, with:

	git clone https://github.com/Karmak23/sparks
	./sparks/1nstall.py

`1nstall` will:

- On OSX, install `Brew`, an up-to-date `Python`, and `git`.
- On Ubuntu and OSX, install a bunch of fancy software to be fully operational in minutes.


## Simple package manager

Sparks provide receipes for all famous package managers. There is a Python library to list/add/remove packages, and a `search` command-line utility. Supported package managers:

- `brew` on OSX, 
- `apt-*` on `Ubuntu` / `Debian`, 
- `npm`, 
- `pip` (2 & 3)
- `gem`.

Adding new packages managers to make `sparks` work on any other systems (eg. `pacman`, `emerge`…) is a matter of minutes.

### Installation

	ln -sf path/to/sparks/utils/pkgmrg.py ~/bin/search

### Usage

	# search for a package, globaly, everywhere:
	search toto

### Implementation note

As of now, only `search` is implemented. `install`, `remove` and other are planned, but would be only aliases to underlying tools and are thus not that useful. 

I currently have shell aliases pointing to `brew` or `apt-*`, given the OS I’m on, and that’s quite satisfying.


## Sparks example with powerline

`powerline-shell` is not that useful per se, but the use-case is quite complex and thus a good example to demonstrate how I use `sparks`.

### The manual and highly personal part

The powerline configuration is stored in my `Dropbox`. You should just copy these lines in your shell and ssh configuration.

In `~/.ssh/config`, I have:

	Host *
		SendEnv POWERLINE_SHELL

In `~/.bashrc`, I have:

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

### Deployment with sparks

Then, i run:

	fab -R lxc-hosts -P -z 5 sys_ssh_powerline

Which will clone the powerline GIT repository on all remote machines, and configure their SSHds to accept the local exported variable.

With that setup, I don't need to run the full `install_powerline` target on them, so they don't get the powerline *font* installed (which is useless on a remote headless server).

And after that, I can enjoy powerline everywhere, but the font is only installed on my laptop or PC.

### If you have any questions, don't hesitate to get in touch, I will be pleased to help.

[![Bitdeli Badge](https://d2weczhvl823v0.cloudfront.net/1flow/sparks/trend.png)](https://bitdeli.com/free "Bitdeli Badge")

