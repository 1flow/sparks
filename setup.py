#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Sparks setup.py. """

import sys

from setuptools import setup, find_packages

if '.' in sys.path:
    sys.path.remove('.')

# We want to be sure that Python will import the sparks from here, and not
# the one eventually installed system-wide or in the current virtualenv.
sys.path.insert(0, '.')

from sparks import version

setup(
    name="sparks",
    version=version,
    author="Olivier Cortès",
    author_email="contact@oliviercortes.com",
    description="My Django project & cloud deployment library (Fabric based)",
    url="https://github.com/Karmak23/sparks",
    packages=find_packages(),
    install_requires=['Fabric', 'charade', 'paramiko', 'mistune',
                      'pyyaml', 'ua-parser', 'user-agents', 'humanize',
                      'djangorestframework', 'beautifulsoup4', ],
    keywords=(
        'installation',
        'management',
        'django',
        'cloud',
        'deployment',
        'bootstraping',
    ),
    license='New BSD',
)
