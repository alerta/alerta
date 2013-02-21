
import stomp

from alerta.common import log as logging
from alerta.common import config

LOG = logging.getLogger(__name__)
CONF = config.CONF


class Messaging(object):
    def connect(self, wait=False):
        try:
            self.connection = stomp.Connection((CONF.stomp_host, CONF.stomp_port))
            self.connection.start()
            self.connection.connect(wait=wait)
        except Exception, e:
            LOG.error('Could not connect to broker %s:%s :', CONF.stomp_host, CONF.stomp_port, e)
            return
        LOG.info('Connected to broker %s:%s', CONF.stomp_host, CONF.stomp_por)

    def send(self, alert):
        try:
            self.connection.send(message=alert.get_body(), headers=alert.get_header(), destination=CONF.stomp_queue)
        except Exception, e:
            LOG.error('Could not send to broker %s:%s :', CONF.stomp_host, CONF.stomp_port, e)
            return
        LOG.info('Message sent to broker %s:%s', CONF.stomp_host, CONF.stomp_port)

    def disconnect(self):
        LOG.info('Disconnecting from broker %s:%s', CONF.stomp_host, CONF.stomp_port)
        self.connection.disconnect()
