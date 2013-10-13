
Introduction
============

Alerta is a monitoring tool that allows alerts from many different systems to be consolidated into a single view.

Currently there are integrations for tools that support standard protocols such as ``SNMP``, ``syslog`` and ``HTTP``.
There are also specific integrations for popular monitoiring tools such as Nagios_, Zabbix_ and Riemann_.

.. _`nagios`: https://github.com/alerta/nagios3-alerta
.. _`zabbix`: https://github.com/alerta/zabbix-alerta
.. _`riemann`: https://github.com/guardian/riemann-config/blob/master/alerta.clj


Installation
============

Installing this package makes available a ``alert-sender`` and ``alert-query`` tool that can be used to send alerts
to the alerta system and to query the alert database::

    $ pip install alerta


Configuration
=============

For a basic configuration that can be used to test the client tools against a demo alerta server, use::

    [DEFAULT]
    timezone = Europe/London
    api_host = api.alerta.io
    api_port = 80

    [alert-query]
    colour = yes

Copy this configuration to ``/etc/alerta/alerta.conf`` or ``$HOME/.alerta.conf`` files::

    $ mv /path/to/alerta.conf.sample $HOME/.alerta.conf

or use the ``ALERTA_CONF`` environment variable::

    $ export ALERTA_CONF=/path/to/alerta.conf


Basic Usage
===========

Abbreviated usage for both commands is shown below::

    usage: alert-sender [-r RESOURCE] [-e EVENT] [-C CORRELATE] [-g GROUP]
                        [-v VALUE] [--status STATUS] [-s SEVERITY] [-E ENV]
                        [-S SERVICE] [-T TAGS] [-t TEXT] [--summary TEXT]
                        [--more TEXT] [--graphs URLS] [-o TIMEOUT]
                        [--type EVENT_TYPE] [-H] [-O ORIGIN] [-q] [-d]


    usage: alert-query [-h] [-c FILE] [--minutes MINUTES] [--hours HOURS]
                       [--days DAYS] [-i ALERTID] [-E ENV] [--not-environment ENV]
                       [-S SERVICE] [--not-service SERVICE] [-r RESOURCE]
                       [--not-resource RESOURCE] [-s SEVERITY]
                       [--not-severity SEVERITY] [--status STATUS]
                       [--not-status STATUS] [-e EVENT] [--not-event EVENT]
                       [-g GROUP] [--not-group GROUP] [--origin ORIGIN]
                       [--not-origin ORIGIN] [-v VALUE] [--not-value VALUE]
                       [-T TAGS] [--not-tags TAGS] [-t TEXT] [--not-text TEXT]
                       [--type EVENT_TYPE] [--not-type TYPE]
                       [--repeat {true,false}] [--show SHOW] [--oneline]
                       [--date DATE] [--format FORMAT] [-o SORTBY] [-w]
                       [-n INTERVAL] [--count LIMIT] [-q QUERY] [--no-header]
                       [--no-footer] [--color] [--output OUTPUT] [-j] [-X] [-d]
                       [--version] [--debug] [--verbose] [--log-dir DIR]
                       [--log-file FILE] [--pid-dir DIR] [--use-syslog]
                       [--use-stderr] [--yaml-config FILE] [--show-settings]


Examples
========

To send a DiskFull warning alert for /tmp on myhost, use::

    $ alert-sender --resource myhost:/tmp --event DiskFull --severity warning

To list all alerts for myhost, use::

    $ alert-query --resource myhost


Trouble-shooting
================

To use ``curl`` to request the same URL for a query, use::

    $ alert-query --dry-run | sh

And for an alert send, use::

    $ alert-sender -r myhost -e test --dry-run | sh


Python API
==========

A python API can be used to generate alerts::

    >>> from alerta.common.api import ApiClient
    >>> from alerta.common.alert import Alert
    >>>
    >>> client = ApiClient(host='api.alerta.io', port=80)
    >>> alert = Alert(resource="foo", event="bar")
    >>>
    >>> client.send(alert)
    u'8e9c4736-c2a8-4b4d-8638-07dad6ed1d2b'
    >>>

The python API can also be used to query for alerts::

    >>> from alerta.common.api import ApiClient
    >>>
    >>> client = ApiClient(host='api.alerta.io', port=80)
    >>> r = client.query()
    >>> r['status']
    u'ok'
    >>> pp = pprint.PrettyPrinter(indent=4)
    >>> pp.pprint(r['alerts']['severityCounts'])
    {   u'cleared': 0,
        u'critical': 1,
        u'debug': 0,
        u'indeterminate': 0,
        u'informational': 0,
        u'major': 2,
        u'minor': 1,
        u'normal': 4,
        u'security': 0,
        u'unknown': 0,
        u'warning': 1}
