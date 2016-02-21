Alerta Release 4.7
==================

[![Build Status](https://travis-ci.org/guardian/alerta.png)](https://travis-ci.org/guardian/alerta) [![Gitter chat](https://badges.gitter.im/alerta/chat.png)](https://gitter.im/alerta/chat)

The Alerta monitoring tool was developed with the following aims in mind:

*   distributed and de-coupled so that it is **SCALABLE**
*   minimal **CONFIGURATION** that easily accepts alerts from any source
*   quick at-a-glance **VISUALISATION** with drill-down to detail

![console](/docs/images/alert-list-rel32.png?raw=true)

Related projects can be found on the Alerta Org Repo at <https://github.com/alerta/>.

----

Requirements
------------

The only mandatory dependency is MongoDB. Everything else is optional.

- MongoDB version 3.x

Optional
--------

A messaging transport that supports AMQP is required *if* it is wanted to send notifications to alert subscribers.
It is recommended to use RabbitMQ, but Redis and even MongoDB have been tested and shown to work.

- RabbitMQ
- Redis
- MongoDB

Note: The default settings use MongoDB so that no additional configuration is required.

Installation
------------

To install MongoDB on Debian/Ubuntu run::

    $ sudo apt-get install -y mongodb-org
    $ mongod

To install the Alerta server and client run::

    $ pip install alerta-server
    $ alertad

To install the web console run::

    $ wget -O alerta-web.tgz https://github.com/alerta/angular-alerta-webui/tarball/master
    $ tar zxvf alerta-web.tgz
    $ cd alerta-angular-alerta-webui-*/app
    $ python -m SimpleHTTPServer 8000

    >> browse to http://localhost:8000

Configuration
-------------

To configure the ``alertad`` server override the default settings using ``~/.alertad.conf``.

Documentation
-------------

More information on configuration and other aspects of alerta can be found at <http://docs.alerta.io>

Tests
-----

To run the tests use::

    $ ALERTA_SVR_CONF_FILE= python -m nose

Cloud Deployment
----------------

Alerta can be deployed to the cloud easily using Heroku, AWS EC2 <https://github.com/alerta/alerta-cloudformation>
or RedHat OpenShift <https://github.com/alerta/openshift-api-alerta>::

[![Deploy](https://www.herokucdn.com/deploy/button.png)](https://heroku.com/deploy)

License
-------

    Alerta monitoring system and console
    Copyright 2012-2016 Guardian News & Media

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
