#!/usr/bin/env python

import setuptools

from alerta import get_version

with open('README.rst') as f:
    long_description = f.read()

setuptools.setup(
    name="alerta",
    version=get_version(),
    description='Alerta monitoring framework',
    long_description=long_description,
    url='https://github.com/guardian/alerta',
    license='Apache License 2.0',
    author='Nick Satterly',
    author_email='nick.satterly@theguardian.com',
    packages=setuptools.find_packages(exclude=['bin', 'tests']),
    install_requires=[
        'argparse',
        'requests',
        'PyYAML',
        'pytz',
        'kombu',
        'pymongo',
        'Flask',
        'irc',
        'boto',
        'suds',
        'dynect',
        'nose'
    ],
    include_package_data=True,
    zip_safe=False,
    scripts=[
        'bin/alert-cloudwatch',
        'bin/alert-dynect',
        'bin/alert-ircbot',
        'bin/alert-logger',
        'bin/alert-mailer',
        'bin/alert-pagerduty',
        'bin/alert-pinger',
        'bin/alert-snmptrap',
        'bin/alert-solarwinds',
        'bin/alert-syslog',
        'bin/alert-urlmon',
        'bin/alerta',
        'bin/alerta-dashboard',
    ],
    keywords='alert monitoring system',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Framework :: Flask',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Telecommunications Industry',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: System :: Monitoring',
    ],
)
