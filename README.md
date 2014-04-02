# Sparks

This is my *foundations* deployment tool and receipes. I use it to bootstrap any new project or machine. It's written in `Python`. Features at a glance:

- a lot of Fabric receipes for Python/Django deployment in LXC/docker enviroments.
- a lot of tasks dedicated to system management (eg. cherry-picked workers restart)
- some receipes for personal machine deployment (eg. my laptop), that you should be able to customize/override/extend with your own. Especially, the `1nstall` script will bootstrap a machine from scratch once the OS is installed.
- a more flexible execution model tha Fabric.
- includes some utility scripts (like a global package search tool, which handles brew, APT, PIP 2&3, Gem and NPM).

See the wiki for deeper explanations, design concepts, etc.

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


If you have any questions, don't hesitate to get in touch, I will be pleased to help.

[![Bitdeli Badge](https://d2weczhvl823v0.cloudfront.net/1flow/sparks/trend.png)](https://bitdeli.com/free "Bitdeli Badge")
