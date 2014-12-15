Alerta Release 3.2
==================

[![Build Status](https://travis-ci.org/satterly/alerta.png)](https://travis-ci.org/satterly/alerta)

The alerta monitoring tool was developed with the following aims in mind:

*   distributed and de-coupled so that it is **SCALABLE**
*   minimal **CONFIGURATION** that easily accepts alerts from any source
*   quick at-a-glance **VISUALISATION** with drill-down to detail

![console](/docs/images/alert-list-rel32.png?raw=true)

More screenshots are available [here](/docs/images/)

Related projects can be found [here][1].

Requirements
------------

The only requirement is MongoDB. Everything else is optional.

- [MongoDB][4]

Optional
--------

A messaging transport that supports AMQP is required for notification to alert subscribers. It is recommended to use RabbitMQ, but Redis and even MongoDB have been tested and shown to work. YMMV.

- [RabbitMQ][2]
- [Redis][3]
- [MongoDB][4]

Note: The default setting uses MongoDB so that no additional configuration is required.

Installation
------------

To install and configure on Debian/Ubuntu:

```
$ sudo apt-get update
$ sudo apt-get install mongodb-server
```

To use RabbitMQ as the message transport instead of the default MongoDB:

```
$ sudo apt-get install rabbitmq-server
```

To install from git:

```
$ git clone https://github.com/guardian/alerta.git alerta
$ cd alerta
$ sudo pip install -r requirements.txt
$ sudo python setup.py install
```

To start the alerta server simply run:

```
$ alertad
```

To send some test alerts run:

```
$ contrib/examples/create-new-alert.sh
```

To view alerts in a terminal run:

```
$ alerta query
```

If the response is `ERROR - 401 Client Error: UNAUTHORIZED` then check the command-line configuration file `~/.alerta.conf`:

```
[DEFAULT]
endpoint = http://localhost:8080
key = demo-key
```

[![Deploy](https://www.herokucdn.com/deploy/button.png)](https://heroku.com/deploy)

More Information
----------------

See the alerta [docs][7]. Documentation is a work in progress. Feedback welcome.

Contribute
----------

If you'd like to contribute to Alerta, start by forking this repo on GitHub.

http://github.com/guardian/alerta

Create a branch for your work and then send us a pull request.

License
-------

    Alerta monitoring system and console
    Copyright 2012 Guardian News & Media

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

[1]: <https://github.com/alerta/> "Alerta GitHub Repo"
[2]: <http://www.rabbitmq.com> "RabbitMQ"
[3]: <http://redis.io/> "Redis"
[4]: <https://www.mongodb.org/> "MongoDB"
[5]: <http://www.elasticsearch.org/> "elasticsearch"
[6]: <http://www.elasticsearch.org/overview/kibana/> "Kibana"
[7]: <http://docs.alerta.io/> "Alerta Documentation"
