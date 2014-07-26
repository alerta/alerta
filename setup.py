#!/usr/bin/env python

import setuptools
import alerta

with open('README.rst') as f:
    readme = f.read()

setuptools.setup(
    name="alerta-server",
    version=alerta.__version__,
    description='Alerta server WSGI application',
    long_description=readme,
    url='https://github.com/guardian/alerta',
    license='Apache License 2.0',
    author='Nick Satterly',
    author_email='nick.satterly@theguardian.com',
    packages=setuptools.find_packages(exclude=['bin', 'tests']),
    install_requires=[
        'Flask',
        'pymongo',
        'kombu',
        'boto',
        'argparse',
        'requests',
        'PyYAML',
        'pytz'
    ],
    include_package_data=True,
    zip_safe=False,
    scripts=[
        'bin/alertad',
    ],
    entry_points={
        'alerta.plugins': [
            'amqp = alerta.plugins.amqp:Messaging',
            'sns = alerta.plugins.sns:SimpleNotificationService',
            'logstash = alerta.plugins.logstash:LogStashOutput',
        ],
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
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: System :: Monitoring',
    ],
)
