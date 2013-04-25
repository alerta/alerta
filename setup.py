#!/usr/bin/env python

import setuptools
from alerta import get_version

setuptools.setup(
    name="alerta",
    version=get_version(),
    description='Alerta monitoring framework',
    url='https://github.com/guardian/alerta',
    license='Apache License 2.0',
    author='Nick Satterly',
    author_email='nick.satterly@guardian.co.uk',
    packages= setuptools.find_packages(exclude=['bin', 'tests']),
    include_package_data=True,
    scripts=['bin/alert-aws',
             'bin/alert-checker',
             'bin/alert-dynect',
             'bin/alert-ircbot',
             'bin/alert-logger',
             'bin/alert-mailer',
             'bin/alert-pagerduty',
             'bin/alert-pinger',
             'bin/alert-query',
             'bin/alert-sender',
             'bin/alert-snmptrap',
             'bin/alert-syslog',
             'bin/alert-urlmon',
             'bin/alerta',
             'bin/alerta-api',
             ],
    keywords='alert monitoring system'
)