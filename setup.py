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
    long_description_content_type='text/markdown',
    url='https://github.com/guardian/alerta',
    license='Apache License 2.0',
    author='Nick Satterly',
    author_email='nick.satterly@gmail.com',
    packages=setuptools.find_packages(exclude=['tests']),
    install_requires=[
        'bcrypt',
        'blinker',
        'cryptography',
        'Flask>=0.10.1',
        'Flask-Compress>=1.4.0',
        'Flask-Cors>=3.0.2',
        'mohawk',
        'PyJWT>=2.0.0',
        'pymongo>=3.6',
        'pyparsing',
        'python-dateutil',
        'pytz',
        'PyYAML',
        'requests',
        'requests-hawk',
        'sentry-sdk[flask]>=0.10.2',
    ],
    extras_require={
        'mongodb': ['pymongo>=3.0'],
        'postgres': ['psycopg2']
    },
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'alertad = alerta.commands:cli'
        ],
        'alerta.plugins': [
            'remote_ip = alerta.plugins.remote_ip:RemoteIpAddr',
            'reject = alerta.plugins.reject:RejectPolicy',
            'heartbeat = alerta.plugins.heartbeat:HeartbeatReceiver',
            'blackout = alerta.plugins.blackout:BlackoutHandler',
            'acked_by = alerta.plugins.acked_by:AckedBy',
            'forwarder = alerta.plugins.forwarder:Forwarder',
            'timeout = alerta.plugins.timeout:TimeoutPolicy'
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
        'Environment :: Web Environment',
        'Environment :: Plugins',
        'Framework :: Flask',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Telecommunications Industry',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.6',
        'Topic :: System :: Monitoring',
    ],
    python_requires='>=3.6'
)
