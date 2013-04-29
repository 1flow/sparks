#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name="sparks",
    version='1.7.5',
    author="Olivier Cortès",
    author_email="contact@oliviercortes.com",
    description="My project/machine bootstrap library",
    url="https://github.com/Karmak23/sparks",

    packages=find_packages(),
    install_requires=['Fabric'],

    keywords=(
        'installation',
        'management',
        'bootstraping',
    ),
    license='New BSD',
)
