
import time
import socket
import threading

from random import random

from alerta.common import log as logging
from alerta.common import config

LOG = logging.getLogger(__name__)
CONF = config.CONF


class Carbon(object):

    carbon_opts = {
        'carbon_host': 'localhost',
        'carbon_port': 2003,
        'carbon_protocol': 'tcp',
        'graphite_prefix': 'alerta.%s' % socket.gethostname(),
    }

    def __init__(self, host=None, port=None, protocol=None, prefix=None):

        config.register_opts(Carbon.carbon_opts)

        self.host = host or CONF.carbon_host
        self.port = port or CONF.carbon_port
        self.protocol = protocol or CONF.carbon_protocol
        self.prefix = prefix or CONF.graphite_prefix

        self.lock = threading.Lock()

        if self.protocol not in ['udp', 'tcp']:
            LOG.error("Protocol must be one of: udp, tcp")
            return

        LOG.info('Carbon setup to send %s packets to %s:%s', self.protocol, self.host, self.port)

        self.addr = (self.host, int(self.port))

        if self.protocol == 'udp':
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        else:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                self.socket.settimeout(0.5)
                self.socket.connect(self.addr)
                self._connected = True
            except (socket.error, socket.timeout):
                self._connected = False
                LOG.warning('Carbon server %s not responding on TCP port %s', self.host, self.port)
            finally:
                self.socket.settimeout(None)

    def metric_send(self, name, value, timestamp=None):

        if name is None or value is None:
            LOG.error('Invalid carbon parameters. Must supply name and value.')
            return

        if self.prefix:
            name = '%s.%s' % (self.prefix, name)

        if not timestamp:
            timestamp = int(time.time())

        LOG.debug('Carbon name=%s, value=%s, timestamp=%s', name, value, timestamp)

        if self.protocol == 'udp':
            try:
                count = self.socket.sendto('%s %s %s\n' % (name, value, timestamp), self.addr)
            except socket.error, e:
                LOG.warning('Failed to send metric to UDP Carbon server %s:%s: %s', self.host, self.port, e)
            else:
                LOG.debug('Sent %s UDP metric packets', count)
        else:
            if not self._connected:
                with self.lock:
                    LOG.info('Attempting reconnect to Carbon server %s:%s', self.host, self.port)
                    try:
                        self.socket.settimeout(0.5)
                        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.socket.connect(self.addr)
                        self._connected = True
                        LOG.info('Reconnected to Carbon server %s on TCP port %s', self.host, self.port)
                    except (socket.error, socket.timeout):
                        LOG.warning('Carbon server %s not responding to TCP port %s', self.host, self.port)
                        self._connected = False
                    finally:
                        self.socket.settimeout(None)

            if self._connected:
                with self.lock:
                    try:
                        self.socket.sendall('%s %s %s\n' % (name, value, timestamp))
                    except socket.error, e:
                        LOG.warning('Failed to send metric to TCP Carbon server %s:%s: %s', self.host, self.port, e)
                        self._connected = False
                    else:
                        LOG.debug('Sent all TCP metric data')

    def shutdown(self):

        if self.protocol == 'tcp':
            self.socket.close()


class StatsD(object):

    statsd_opts = {
        'statsd_host': 'localhost',
        'statsd_port': 8125,
        'graphite_prefix': 'alerta.%s' % socket.gethostname(),
    }

    def __init__(self, host=None, port=None, rate=1, prefix=None):

        config.register_opts(StatsD.statsd_opts)

        self.host = host or CONF.statsd_host
        self.port = port or CONF.statsd_port
        self.rate = rate
        self.prefix = prefix or CONF.graphite_prefix

        LOG.info('Statsd setup to send packets to %s:%s with sample rate of %d', self.host, self.port, self.rate)

        self.addr = (self.host, int(self.port))
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def metric_send(self, name, value, mtype=None, rate=None):
        """
        >>> statsd = StatsD()
        >>> statsd.metric_send('gorets', 1, 'c', 0.1)  # counters  => 'gorets:1|c@0.1'
        >>> statsd.metric_send('glork', 320, 'ms')     # timers    => 'glork:320|ms'
        >>> statsd.metric_send('gaugor', 333, 'g')     # gauge     => 'gaugor:333|g'
        >>> statsd.metric_send('gaugor', -10, 'g')     # gauge dec => 'gaugor:-10|g'
        >>> statsd.metric_send('gaugor', '+4', 'g')    # gauge inc => 'gaugor:+4|g'
        >>> statsd.metric_send('uniques', 765, 's')    # sets      => 'uniques:765|s
        """

        if self.prefix:
            name = '%s.%s' % (self.prefix, name)

        mtype = mtype or 'c'  # default is 'counter'
        rate = rate or self.rate

        LOG.debug('Statsd name=%s, value=%s, type=%s rate=%s', name, value, mtype, rate)

        data = '%s:%s|%s' % (name, value, mtype)

        if rate < 1:
            if random() <= rate:
                data = '%s|@%s' % (data, rate)
            else:
                return

        LOG.debug('Statsd metric send: %s', data)
        try:
            self.socket.sendto(data.encode('utf-8'), self.addr)
        except socket.error, e:
            LOG.warning('Failed to send metric to UDP Statsd server %s:%s: %s', self.host, self.port, e)

