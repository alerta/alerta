#!/usr/bin/env python

import os
import subprocess
from datetime import datetime

import setuptools


def read(filename):
    return open(os.path.join(os.path.dirname(__file__), filename)).read()


try:
    with open('alerta/build.py', 'w') as f:
        build = """
        BUILD_NUMBER = '{build_number}'
        BUILD_DATE = '{date}'
        BUILD_VCS_NUMBER = '{revision}'
        """.format(
            build_number=os.environ.get('BUILD_NUMBER', 'PROD'),
            date=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            revision=subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('utf-8').strip()
        ).replace('    ', '')
        f.write(build)
except Exception:
    pass

setuptools.setup(
    name='alerta-server',
    version=read('VERSION'),
    description='Alerta server WSGI application',
    long_description=read('README.md'),
    url='https://github.com/guardian/alerta',
    license='Apache License 2.0',
    author='Nick Satterly',
    author_email='nick.satterly@theguardian.com',
    packages=setuptools.find_packages(exclude=['tests']),
    install_requires=[
        'Flask>=0.10.1',
        'Flask-Cors>=3.0.2',
        'Flask-Compress>=1.4.0',
        'raven[flask]>=6.2.1',
        'pymongo>=3.0',
        'psycopg2',
        'pyparsing',
        'requests',
        'python-dateutil',
        'pytz',
        'PyJWT',
        'pyyaml',
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
        ],
        'alerta.webhooks': [
            'cloudwatch = alerta.webhooks.cloudwatch:CloudWatchWebhook',
            'grafana = alerta.webhooks.grafana:GrafanaWebhook',
            'graylog = alerta.webhooks.graylog:GraylogWebhook',
            'newrelic = alerta.webhooks.newrelic:NewRelicWebhook',
            'pagerduty = alerta.webhooks.pagerduty:PagerDutyWebhook',
            'pingdom = alerta.webhooks.pingdom:PingdomWebhook',
            'prometheus = alerta.webhooks.prometheus:PrometheusWebhook',
            'riemann = alerta.webhooks.riemann:RiemannWebhook',
            'serverdensity = alerta.webhooks.serverdensity:ServerDensityWebhook',
            'slack = alerta.webhooks.slack:SlackWebhook',
            'stackdriver = alerta.webhooks.stackdriver:StackDriverWebhook',
            'telegram = alerta.webhooks.telegram:TelegramWebhook'
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
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.5',
        'Topic :: System :: Monitoring',
    ],
    python_requires='>=3.5'
)
