#!/usr/bin/env python

from setuptools import setup
from alerta import get_version

setup(
    name="Alerta",
    version=get_version(),
    packages= ['alerta'],
    description='Alerta monitoring framework',
    license='Apache License 2.0',
    url='https://github.com/guardian/alerta',
    author='Nick Satterly',
    author_email='nick.satterly@guardian.co.uk',
    keywords='alert monitoring system'
)