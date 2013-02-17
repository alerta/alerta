#!/usr/bin/env python

from setuptools import setup
from alerta import get_version

setup(
    name="alerta",
    version=get_version(),
    description='Alerta monitoring framework',
    url='https://github.com/guardian/alerta',
    license='Apache License 2.0',
    author='Nick Satterly',
    author_email='nick.satterly@guardian.co.uk',
    packages= ['alerta'],
    entry_points={
        'console_scripts': [
            'alert = alerta.shell:main'
        ],
    },
    keywords='alert monitoring system'
)