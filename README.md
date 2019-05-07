Alerta Release 7.0
==================

[![Build Status](https://travis-ci.org/alerta/alerta.png)](https://travis-ci.org/alerta/alerta)
[![Gitter chat](https://badges.gitter.im/alerta/chat.png)](https://gitter.im/alerta/chat)

The Alerta monitoring tool was developed with the following aims in mind:

*   distributed and de-coupled so that it is **SCALABLE**
*   minimal **CONFIGURATION** that easily accepts alerts from any source
*   quick at-a-glance **VISUALISATION** with drill-down to detail

![webui](/docs/images/alerta-webui-v7.jpg?raw=true)

----

Python 2.7 support is EOL
-------------------------

Starting with Release 6.0 only Python 3.5+ is supported. Release 5.2 was the
last to support Python 2.7 and feature enhancements for this release ended on
August 31, 2018. Only critical bug fixes will be backported to Release 5.2.

Requirements
------------

The only mandatory dependency is MongoDB or PostgreSQL. Everything else is optional.

- Postgres version 9.5 or better
- MongoDB version 3.2 or better

Installation
------------

To install MongoDB on Debian/Ubuntu run:

    $ sudo apt-get install -y mongodb-org
    $ mongod

To install MongoDB on CentOS/RHEL run:

    $ sudo yum install -y mongodb
    $ mongod

To install the Alerta server and client run:

    $ pip install alerta-server alerta
    $ alertad run

To install the web console run:

    $ wget https://github.com/alerta/alerta-webui/releases/latest/download/alerta-webui.tar.gz
    $ tar zxvf alerta-webui.tar.gz
    $ cd dist
    $ python3 -m http.server 8000

    >> browse to http://localhost:8000

### Docker
Alerta and MongoDB can also run using Docker containers, see [alerta/docker-alerta](https://github.com/alerta/docker-alerta).

Configuration
-------------

To configure the ``alertad`` server override the default settings in ``/etc/alertad.conf``
or using ``ALERTA_SVR_CONF_FILE`` environment variable::

    $ ALERTA_SVR_CONF_FILE=~/.alertad.conf
    $ echo "DEBUG=True" > $ALERTA_SVR_CONF_FILE

Documentation
-------------

More information on configuration and other aspects of alerta can be found
at <http://docs.alerta.io>

Development
-----------

To run in development mode, listening on port 5000:

    $ export FLASK_APP=alerta FLASK_ENV=development
    $ pip install -e .
    $ flask run

To run in development mode, listening on port 8080, using Postgres and
reporting errors to [Sentry](https://sentry.io):

    $ export FLASK_APP=alerta FLASK_ENV=development
    $ export DATABASE_URL=postgres://localhost:5432/alerta5
    $ export SENTRY_DSN=https://8b56098250544fb78b9578d8af2a7e13:fa9d628da9c4459c922293db72a3203f@sentry.io/153768
    $ pip install -e .[postgres]
    $ flask run --debugger --port 8080 --with-threads --reload

Troubleshooting
---------------

Enable debug log output by setting `DEBUG=True` in the API server
configuration:

```
DEBUG=True

LOG_HANDLERS = ['console','file']
LOG_FORMAT = 'verbose'
LOG_FILE = '$HOME/alertad.log'
```

It can also be helpful to check the web browser developer console for
JavaScript logging, network problems and API error responses.

Tests
-----

To run the tests using a local Postgres database run:

    $ pip install -r requirements.txt
    $ pip install -e .[postgres]
    $ createdb test5
    $ ALERTA_SVR_CONF_FILE= DATABASE_URL=postgres:///test5 nosetests

Cloud Deployment
----------------

Alerta can be deployed to the cloud easily using Heroku <https://github.com/alerta/heroku-api-alerta>,
AWS EC2 <https://github.com/alerta/alerta-cloudformation>, or Google Cloud Platform
<https://github.com/alerta/gcloud-api-alerta>

License
-------

    Alerta monitoring system and console
    Copyright 2012-2019 Nick Satterly

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
