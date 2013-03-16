# Sparks

My *foundations* repository, which I use to bootstrap any new project or machine. Written in `Python`.

- Uses [Fabric](http://fabfile.org/) to deploy.
- Can deploy many machines at a time.
- Works on Ubuntu and OSX *hosts* and *targets* (I use both, daily).
- Is implemented with a lot of tasks and subtasks, which can be re-used to your liking.
- Deploies graphical, console and server tools.
- Contains a unified package search tool (`utils/pkgmgr.py`, see below).
- will contain some modules for bootstraping `Django` projects quickly.
- will likely contain some `AngularJS` modules, too.

## How-to

Note: on OSX, you will have a chicken-and-egg problem, because `git` is not installed by default. I personally solves this by installing `Dropbox` first, which contains an up-to-date copy of this `sparks` repository, and data files installed by it, which are highly personnal (some contains passwords or hashes). On Ubuntu, just `sudo apt-get install git-core` and you're ready to shine.

### First installation on a brand new machine

	git clone git://github.com/Karmak23/sparks.git
	./sparks/1nstall.py

	# and let it flow…

### Later

	fab list
	# a bunch of options are available…

	fab myenv
	# or anything you need…
	
### Simple package manager

Command-line utility, which handles `brew` on OSX, `apt-*` on `Ubuntu` / `Debian`, `npm`, `pip` and `gem`.

#### Installation

	ln -sf path/to/sparks/utils/pkgmrg.py ~/bin/search
	
#### Usage

	# search for a package, globaly, everywhere:
	search toto
	
As of now, only `search` is implemented. `install`, `remove` and other are planned, but would be only aliases to underlying tools and are thus not that useful. I currently have shell aliases pointing to `brew` or `apt-*`, given the OS I’m on, and that’s quite satisfying.