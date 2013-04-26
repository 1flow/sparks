#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name="sparks",
    author="Olivier Cortès",
    author_email="contact@oliviercortes.com",
    description="My project/machine bootstrap library",
    url="https://github.com/Karmak23/sparks",

    packages=find_packages(),
    install_requires=['Django', 'Fabric'],

    keywords=(
        'installation',
        'management',
        'bootstraping',
    ),
    license='New BSD',
)
