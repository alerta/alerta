
import stomp

from alerta.common import log as logging
from alerta.common import config

LOG = logging.getLogger(__name__)
CONF = config.CONF


class Messaging(object):
    def connect(self, wait=False):
        try:
            self.connection = stomp.Connection([(CONF.stomp_host, CONF.stomp_port)])
            self.connection.start()
            self.connection.connect(wait=wait)
        except Exception, e:
            LOG.error('Could not connect to broker %s:%s : %s', CONF.stomp_host, CONF.stomp_port, e)
            return

        LOG.info('Connected to broker %s:%s', CONF.stomp_host, CONF.stomp_port)

    def send(self, alert):

        LOG.debug('header = %s', alert.get_header())
        LOG.debug('message = %s', alert.get_body())

        try:
            self.connection.send(message=alert.get_body(), headers=alert.get_header(), destination=CONF.stomp_queue)
        except Exception, e:
            LOG.error('Could not send to broker %s:%s : %s', CONF.stomp_host, CONF.stomp_port, e)
            return
        LOG.info('Message sent to broker %s:%s', CONF.stomp_host, CONF.stomp_port)

    def disconnect(self):
        if self.connection.is_connected():
            LOG.info('Disconnecting from broker %s:%s', CONF.stomp_host, CONF.stomp_port)
            self.connection.disconnect()
        LOG.info('Disconnected!')
