
import time
import socket

from random import random

from alerta.common import log as logging
from alerta.common import config

LOG = logging.getLogger(__name__)
CONF = config.CONF


class Carbon(object):

    def __init__(self, host=None, port=None, protocol=None):

        self.host = host or CONF.carbon_host
        self.port = port or CONF.carbon_port
        self.protocol = protocol or CONF.carbon_protocol

        if self.protocol not in ['udp', 'tcp']:
            LOG.error("Protocol must be one of: udp, tcp")
            return

        LOG.debug('Carbon setup to send %s packets to %s:%s', self.protocol, self.host, self.port)

        self.addr = (self.host, int(self.port))

        if protocol == 'udp':
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        else:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                self.socket.connect(self.addr)
                self._connected = True
            except socket.error:
                self._connected = False
                LOG.warning('Carbon server %s not responding on TCP port %s', self.host, self.port)

    def metric_send(self, name, value, timestamp=None):

        if name is None or value is None:
            LOG.error('Invalid carbon parameters. Must supply name and value.')
            return

        if not timestamp:
            timestamp = int(time.time())

        if CONF.graphite_prefix and len(CONF.graphite_prefix) > 0:
            prefix = CONF.graphite_prefix + '.'
        else:
            prefix = ''

        LOG.debug('Carbon name=%s%s, value=%s, timestamp=%s', prefix, name, value, timestamp)

        if self.protocol == 'udp':
            try:
                count = self.socket.sendto('%s%s %s %s\n' % (prefix, name, value, timestamp), self.addr)
            except socket.error, e:
                LOG.error('Failed to send metric to UDP Carbon server %s:%s: %s', self.host, self.port, e)
            else:
                LOG.debug('Sent %s UDP metric packets', count)
        else:
            if not self._connected:
                LOG.info('Attempting reconnect to Carbon server %s:%s', self.host, self.port)
                try:
                    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.socket.connect(self.addr)
                    self._connected = True
                    LOG.info('Reconnected to Carbon server %s on TCP port %s', self.host, self.port)
                except socket.error:
                    LOG.warning('Carbon server %s not responding to TCP port %s', self.host, self.port)
                    self._connected = False
                    return

            if self._connected:
                try:
                    self.socket.sendall('%s %s %s\n' % (name, value, timestamp))
                except socket.error, e:
                    LOG.warning('Failed to send metric to TCP Carbon server %s:%s: e', self.host, self.port, e)
                    self._connected = False
                else:
                    LOG.debug('Sent all TCP metric data')

    def shutdown(self):

        if self.protocol == 'tcp':
            self.socket.close()


class StatsD(object):

    def __init__(self, host=None, port=None, rate=1):

        self.host = host or CONF.statsd_host
        self.port = port or CONF.statsd_port
        self.rate = rate

        LOG.debug('Statsd setup to send packets to %s:%s with sample rate of %d', self.host, self.port, self.rate)

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

        mtype = mtype or 'c'  # default is 'counter'
        rate = rate or self.rate


        if CONF.graphite_prefix and len(CONF.graphite_prefix) > 0:
            prefix = CONF.graphite_prefix + '.'
        else:
            prefix = ''

        LOG.debug('Statsd name=%s%s, value=%s, type=%s rate=%s', prefix, name, value, mtype, rate)

        data = '%s%s:%s|%s' % (prefix, name, value, mtype)

        if rate < 1:
            if random() <= rate:
                data = '%s|@%s' % (data, rate)
            else:
                return

        LOG.debug('Statsd metric send: %s', data)
        self.socket.sendto(data.encode('utf-8'), self.addr)
