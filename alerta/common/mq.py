import time
import json
import stomp

from alerta.common import log as logging
from alerta.common import config
from alerta.common.utils import DateEncoder

LOG = logging.getLogger('stomp.py')
CONF = config.CONF


class Messaging(object):

    def __init__(self):
        logging.setup('stomp.py')

    def connect(self, callback=None, wait=False):
        self.callback = callback
        self.wait = wait
        try:
            self.connection = stomp.Connection([(CONF.stomp_host, CONF.stomp_port)])
            if self.callback:
                self.connection.set_listener('', self.callback)
            self.connection.start()
            self.connection.connect(wait=self.wait)
        except Exception, e:
            LOG.error('Could not connect to broker %s:%s : %s', CONF.stomp_host, CONF.stomp_port, e)
            return

        LOG.info('Connected to broker %s:%s', CONF.stomp_host, CONF.stomp_port)

    def reconnect(self):
        try:
            self.connection = stomp.Connection([(CONF.stomp_host, CONF.stomp_port)])
            if self.callback:
                self.connection.set_listener('', self.callback)
            self.connection.start()
            self.connection.connect(wait=self.wait)
        except Exception, e:
            LOG.error('Could not connect to broker %s:%s : %s', CONF.stomp_host, CONF.stomp_port, e)
            return

        LOG.info('Connected to broker %s:%s', CONF.stomp_host, CONF.stomp_port)

    def subscribe(self, destination=None, ack='auto'):

        self.destination = destination or CONF.inbound_queue

        self.connection.subscribe(destination=self.destination, ack=ack)

    def send(self, alert, destination=None):

        self.destination = destination or CONF.inbound_queue

        LOG.debug('header = %s', alert.get_header())
        LOG.debug('message = %s', alert.get_body())

        while not self.connection.is_connected():
            LOG.warning('Waiting for message broker to become available...')
            time.sleep(0.1)

        LOG.debug('Sending alert to message broker...')
        try:
            self.connection.send(message=json.dumps(alert.get_body(), cls=DateEncoder), headers=alert.get_header(),
                                 destination=self.destination)
        except Exception, e:
            LOG.error('Could not send to broker %s:%s : %s', CONF.stomp_host, CONF.stomp_port, e)
            return
        LOG.info('Message sent to broker %s:%s', CONF.stomp_host, CONF.stomp_port)

    def disconnect(self):
        if self.connection.is_connected():
            LOG.info('Disconnecting from broker %s:%s', CONF.stomp_host, CONF.stomp_port)
            self.connection.disconnect()
        LOG.info('Disconnected!')


class MessageHandler(object):
    """
    A generic message handler class.

    Usage: Subclass the MessageHandler class and override the on_message() method
    """

    def on_connecting(self, host_and_port):
        LOG.info('Connecting to %s', host_and_port)

    def on_connected(self, headers, body):
        LOG.info('Connected to %s %s', headers, body)

    def on_disconnected(self):
        # TODO(nsatterl): auto-reconnect
        LOG.error('Connection to messaging server has been lost.')

    def on_message(self, headers, body):
        LOG.info("Received message %s %s", headers, body)

    def on_receipt(self, headers, body):
        LOG.debug('Receipt received %s %s', headers, body)

    def on_error(self, headers, body):
        LOG.error('Error %s %s', headers, body)

    def on_send(self, headers, body):
        LOG.debug('Sending message %s %s', headers, body)

