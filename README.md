Alerta monitoring system and console
====================================

[![Build Status](https://travis-ci.org/satterly/alerta.png)](https://travis-ci.org/satterly/alerta)

The alerta monitoring tool was developed with the following aims in mind:

*   distributed and de-coupled so that it is **SCALABLE**
*   minimal **CONFIGURATION** that easily accepts alerts from any source
*   quick at-a-glance **VISUALISATION** with drill-down to detail

![console](/doc/images/alerta-console-small.png?raw=true)

More screenshots are available [here](/doc/images/)

Requirements
------------

- [ActiveMQ][1] or [RabbitMQ][2] ie. a message broker that supports STOMP
- [MongoDB][3]

Installation
------------

The backend components are written in Python and the web frontend in JavaScript so there is nothing to compile.

To install and configure the requirements on Debian/Ubuntu:

```
$ sudo apt-get install mongodb-server

```

To use RabbitMQ with STOMP plugin enabled and configure the broker:

```
$ sudo apt-get install rabbitmq-server
$ sudo /usr/lib/rabbitmq/bin/rabbitmq-plugins enable rabbitmq_stomp
$ sudo service rabbitmq-server restart
$ wget http://guest:guest@localhost:55672/cli/rabbitmqadmin && chmod +x rabbitmqadmin
$ ./rabbitmqadmin declare exchange name=alerts type=fanout
```

To use Apache ActiveMQ with STOMP transport enabled and configure the broker:

```
$ wget http://mirror.rmg.io/apache/activemq/apache-activemq/5.8.0/apache-activemq-5.8.0-bin.tar.gz
$ tar zxvf apache-activemq-5.8.0-bin.tar.gz && cd apache-activemq-5.8.0
$ sudo bin/activemq console xbean:conf/activemq-stomp.xml
```

To run Alerta in a python virtual environment:

```
$ pip install virtualenv
$ pip install virtualenvwrapper
$ export WORKON_HOME=$HOME/.virtualenvs
$ mkdir -p $WORKON_HOME
$ source /usr/local/bin/virtualenvwrapper.sh
$ mkvirtualenv alerta
```

To install and configure a test implementation of alerta:

```
$ git clone git://github.com/guardian/alerta.git alerta
$ cd alerta
$ pip install -r requirements.txt
$ python setup.py install
```

To start alerta with a configuration that logs to /tmp:

```
$ alerta --log-dir=/tmp
$ alerta-api --log-dir=/tmp
```

To run in the foreground:

```
$ alerta --log-dir=/tmp --debug --foreground --use-stderr
$ alerta-api --log-dir=/tmp --debug --use-stderr
```

To use the alert console modify `$HOME/.alerta.conf` so that the API uses a free port and static content can be found:
```
[DEFAULT]
api_port = 8000

[alerta-api]
dashboard_dir = /path/to/alerta/dashboard/v2/assets/
```

If using Apache ActiveMQ change the inbound queue from an AMQP exchange to a STOMP queue:
```
[DEFAULT]
inbound_queue = /queue/alerts
```

For example, if the repo was cloned to `/home/foobar/git/alerta` then the `dashboard_dir` directory path will be `/home/foobar/git/alerta/dashboard/v2/assets/`.

And then the alert console can be found at:

````
http://localhost:8000/alerta/dashboard/v2/console.html
```

To see some test alerts in the console run:

```
$ contrib/examples/create-new-alert.sh
```

Optional (for alert history)
--------

- [elasticsearch][4]
- [Kibana][5]

> Note: None of these packages require special configuration to work with Alerta.

More Information
----------------

See the alerta [wiki][6]

Contribute
----------

If you'd like to hack on Alerta, start by forking this repo on GitHub.

http://github.com/guardian/alerta

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

[1]: <http://activemq.apache.org/> "Apache ActiveMQ"
[2]: <http://www.rabbitmq.com> "RabbitMQ"
[3]: <http://www.10gen.com/> "10gen MongoDB"
[4]: <http://www.elasticsearch.org/> "elasticsearch"
[5]: <https://github.com/rashidkpc/Kibana> "Kibana"
[6]: <https://github.com/guardian/alerta/wiki> "Alerta wiki"
