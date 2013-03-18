Alerta monitoring system and console
====================================

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
$ sudo apt-get install rabbitmq-server
```

To enable STOMP in RabbitMQ and configure the broker:

```
$ sudo /usr/lib/rabbitmq/bin/rabbitmq-plugins enable rabbitmq_stomp
$ sudo service rabbitmq-server restart
$ wget http://guest:guest@localhost:55672/cli/rabbitmqadmin && chmod +x rabbitmqadmin
$ ./rabbitmqadmin declare exchange name=alerts type=fanout
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
$ bin/alerta --log-dir=/tmp
$ bin/alerta-api --log-dir=/tmp
```

To run in the foreground:

```
$ bin/alerta --log-dir=/tmp --debug --foreground --use-stderr
$ bin/alerta-api --log-dir=/tmp --debug --use-stderr
```

To use the alert consoles modify `$HOME/.alerta.conf` like so:
```
[alerta-api]
dashboard_dir = /path/to/alerta/dashboard
```

And then the alert consoles can be found:

````
http://localhost:5000/alerta/dashboard/v1/console.html
http://localhost:5000/alerta/dashboard/v1/console.html
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
