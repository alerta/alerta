
import time
import socket

from alerta.common import log as logging
from alerta.common import config

LOG = logging.getLogger(__name__)
CONF = config.CONF

PROTOCOLS = [
    'udp',
    'tcp'
]


class Carbon(object):

    def __init__(self, host=None, port=None, protocol=None):

        self.host = host or CONF.carbon_host
        self.port = port or CONF.carbon_port
        self.protocol = protocol or CONF.carbon_protocol

        if self.protocol not in PROTOCOLS:
            LOG.error("Protocol must be one of: %s", ','.join(PROTOCOLS))
            return

        LOG.debug('Carbon setup to send %s packets to %s:%s', self.protocol, self.host, self.port)

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.hostport = (self.host, int(self.port))

    def metric_send(self, name, value, timestamp=None):

        if name is None or value is None:
            LOG.error('Invalid carbon parameters. Must supply name and value.')
            return

        if not timestamp:
            timestamp = int(time.time())

        LOG.debug('carbon name=%s, value=%s, timestamp=%s', name, value, timestamp)
        count = self.socket.sendto('%s %s %s\n' % (name, value, timestamp), self.hostport)
        LOG.debug('Sent %s data packets', count)

