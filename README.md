alerta-ng Release 9.1
=====================

> **This is alerta-ng, a community-maintained fork of [Alerta](https://github.com/alerta/alerta).**
>
> The upstream project is no longer actively maintained — issues and pull requests are not
> being reviewed or released. alerta-ng exists to keep the project moving: merging fixes that
> are already sitting unmerged upstream, keeping dependencies and supported Python versions
> current, and continuing to develop the application for production use.
>
> alerta-ng is a drop-in replacement: the importable package is still `alerta`, and the
> `alerta.plugins` and `alerta.webhooks` entry points are unchanged, so existing plugins and
> deployments keep working.
>
> alerta-ng is not affiliated with, endorsed by, or supported by the upstream maintainers.
> Please report issues here, not on the upstream tracker.


[![Tests](https://github.com/ospo-ionik/alerta-ng/actions/workflows/tests.yml/badge.svg)](https://github.com/ospo-ionik/alerta-ng/actions/workflows/tests.yml)
[![Lint](https://github.com/ospo-ionik/alerta-ng/actions/workflows/lint.yml/badge.svg)](https://github.com/ospo-ionik/alerta-ng/actions/workflows/lint.yml)
[![CodeQL](https://github.com/ospo-ionik/alerta-ng/actions/workflows/analysis.yml/badge.svg)](https://github.com/ospo-ionik/alerta-ng/actions/workflows/analysis.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

The Alerta monitoring tool was developed with the following aims in mind:

*   distributed and de-coupled so that it is **SCALABLE**
*   minimal **CONFIGURATION** that easily accepts alerts from any source
*   quick at-a-glance **VISUALISATION** with drill-down to detail

![webui](/docs/images/alerta-webui-v7.jpg?raw=true)

----

Requirements
------------

Release 9 only supports Python 3.9 or higher.

The only mandatory dependency is MongoDB or PostgreSQL. Everything else is optional.

- Postgres version 13 or better
- MongoDB version 6.0 or better

Installation
------------

To install MongoDB on Debian/Ubuntu run:

    $ sudo apt-get install -y mongodb-org
    $ mongod

To install MongoDB on CentOS/RHEL run:

    $ sudo yum install -y mongodb
    $ mongod

To install the alerta-ng server and the Alerta client run:

    $ pip install alerta-ng-server alerta
    $ alertad run

Note that `alerta-ng-server` replaces the upstream `alerta-server` distribution: both
install the same `alerta` package, so they cannot be installed side by side. Uninstall
`alerta-server` first when migrating an existing environment. The `alerta` client above
is the unmodified upstream CLI and is unaffected.

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
at <https://docs.alerta.io>. Those are the upstream project's docs; they
describe the codebase alerta-ng is forked from and remain accurate for
anything alerta-ng has not changed. Differences introduced by this fork are
documented in [CHANGELOG.md](CHANGELOG.md).

Development
-----------

To run in development mode, listening on port 5000:

    $ export FLASK_APP=alerta FLASK_DEBUG=1
    $ pip install -e .
    $ flask run

To run in development mode, listening on port 8080, using Postgres and
optionally reporting errors to [Sentry](https://sentry.io) (set `SENTRY_DSN`
to your own project's DSN; error reporting is disabled when it is unset):

    $ export FLASK_APP=alerta FLASK_DEBUG=1
    $ export DATABASE_URL=postgres://localhost:5432/alerta5
    $ export SENTRY_DSN=https://<key>@<organisation>.ingest.sentry.io/<project>
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

To run the *all* the tests there must be a local Postgres
and MongoDB database running. Then run:

    $ TOXENV=ALL make test

To just run the Postgres or MongoDB tests run:

    $ TOXENV=postgres make test
    $ TOXENV=mongodb make test

To run a single test run something like:

    $ TOXENV="mongodb -- tests/test_search.py::QueryParserTestCase::test_boolean_operators" make test
    $ TOXENV="postgres -- tests/test_queryparser.py::PostgresQueryTestCase::test_boolean_operators" make test

Cloud Deployment
----------------

Alerta can be deployed to the cloud easily using Heroku <https://github.com/alerta/heroku-api-alerta>,
AWS EC2 <https://github.com/alerta/alerta-cloudformation>, or Google Cloud Platform
<https://github.com/alerta/gcloud-api-alerta>

License
-------

    Alerta monitoring system and console
    Copyright 2012-2023 Nick Satterly

    This distribution is alerta-ng, a fork of that project. Portions of this
    software have been modified from the original work.
    Modifications Copyright 2026 the alerta-ng contributors.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
