#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name="sparks",
    version='2.7.1',
    author="Olivier Cortès",
    author_email="contact@oliviercortes.com",
    description="My Django project & cloud deployment library (Fabric based)",
    url="https://github.com/Karmak23/sparks",
    packages=find_packages(),
    install_requires=['Fabric'],
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
