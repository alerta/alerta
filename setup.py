#!/usr/bin/env python

import os
import subprocess
from datetime import datetime

import setuptools

with open('VERSION') as f:
    version = f.read().strip()

with open('README.md') as f:
    readme = f.read()

try:
    with open('alerta/build.py', 'w') as f:
        build = """
        BUILD_NUMBER = '{build_number}'
        BUILD_DATE = '{date}'
        BUILD_VCS_NUMBER = '{revision}'
        """.format(
            build_number=os.environ.get('BUILD_NUMBER', 'PROD'),
            date=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            revision=subprocess.check_output(["git", "rev-parse", "HEAD"]).decode('utf-8').strip()
        ).replace('    ', '')
        f.write(build)
except Exception:
    pass

setuptools.setup(
    name='alerta-server',
    version=version,
    description='Alerta server WSGI application',
    long_description=readme,
    url='https://github.com/guardian/alerta',
    license='Apache License 2.0',
    author='Nick Satterly',
    author_email='nick.satterly@theguardian.com',
    packages=setuptools.find_packages(exclude=['tests']),
    install_requires=[
        'Flask>=0.10.1',
        'Flask-Cors>=3.0.2',
        'Flask-Compress>=1.4.0',
        'raven[flask]==6.1.0',
        'pymongo>=3.0',
        'psycopg2',
        'argparse',
        'requests',
        'python-dateutil',
        'pytz',
        'PyJWT',
        'bcrypt'
    ],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'alertad = alerta.commands:cli'
        ],
        'alerta.plugins': [
            'reject = alerta.plugins.reject:RejectPolicy',
            'blackout = alerta.plugins.blackout:BlackoutHandler'
        ]
    },
    keywords='alert monitoring system wsgi application api',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Framework :: Flask',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Telecommunications Industry',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 2.7',
        'Topic :: System :: Monitoring',
    ],
)
