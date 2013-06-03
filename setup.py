#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name="sparks",
    version='2.3.1',
    author="Olivier Cortès",
    author_email="contact@oliviercortes.com",
    description="My project/machine bootstrap library",
    url="https://github.com/Karmak23/sparks",

    packages=find_packages(),
    install_requires=['-e git+https://github.com/Karmak23/fabric#egg=fabric'],

    keywords=(
        'installation',
        'management',
        'bootstraping',
    ),
    license='New BSD',
)
