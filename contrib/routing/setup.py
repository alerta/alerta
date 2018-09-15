#!/usr/bin/env python

import setuptools

version = '0.0.1'

setuptools.setup(
    name='alerta-routing',
    version=version,
    description='Alerta routing rules for plugins',
    url='https://github.com/alerta/alerta-contrib',
    license='Apache License 2.0',
    author='Nick Satterly',
    author_email='nick.satterly@theguardian.com',
    py_modules=['routing'],
    install_requires=[
        'requests',
        'alerta-server'
    ],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'alerta.routing': [
            'rules = routing:rules'
        ]
    }
)
