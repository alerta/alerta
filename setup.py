#!/usr/bin/env python

import setuptools

with open('VERSION') as f:
    version = f.read().strip()

with open('README.rst') as f:
    readme = f.read()

setuptools.setup(
    name='alerta-server',
    namespace_packages=['alerta'],
    version=version,
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
        'pytz',
        'alerta'
    ],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'alertad = alerta.app:main'
        ],
        'alerta.plugins': [
            'reject = alerta.plugins.reject:RejectPolicy',
            'amqp = alerta.plugins.amqp:FanoutPublisher',
            'sns = alerta.plugins.sns:SnsTopicPublisher',
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
