
import json
import stomp
from stomp import exception, ConnectionListener

from alerta.common import log as logging
from alerta.common import config
from alerta.common.utils import DateEncoder

LOG = logging.getLogger('stomp.py')
CONF = config.CONF

_RECONNECT_SLEEP_INITIAL = 2  # seconds
_RECONNECT_SLEEP_INCREASE = 2
_RECONNECT_SLEEP_MAX = 300    # seconds
_RECONNECT_ATTEMPTS_MAX = 20


class Messaging(object):

    mq_opts = {
        'stomp_host': 'localhost',
        'stomp_port': 61613,

        'inbound_queue': '/exchange/alerts',
        'outbound_queue': '/queue/logger',
        'outbound_topic': '/topic/notify',

        'rabbit_host': 'localhost',
        'rabbit_port': 5672,
        'rabbit_use_ssl': False,
        'rabbit_userid': 'guest',
        'rabbit_password': 'guest',
        'rabbit_virtual_host': '/',
    }

    def __init__(self):

        config.register_opts(Messaging.mq_opts)

        logging.setup('stomp.py')

    def connect(self, callback=None, wait=False):
        self.callback = callback
        self.wait = wait
        try:
            self.conn = stomp.Connection(
                [(CONF.stomp_host, int(CONF.stomp_port))],
                reconnect_sleep_initial=_RECONNECT_SLEEP_INITIAL,
                reconnect_sleep_increase=_RECONNECT_SLEEP_INCREASE,
                reconnect_sleep_max=_RECONNECT_SLEEP_MAX,
                reconnect_attempts_max=_RECONNECT_ATTEMPTS_MAX
            )
            if self.callback:
                self.conn.set_listener('', self.callback)
            self.conn.start()
            self.conn.connect(wait=self.wait)
        except Exception, e:
            LOG.error('Could not connect to broker %s:%s : %s', CONF.stomp_host, CONF.stomp_port, e)
            return

        LOG.info('Connected to broker %s:%s', CONF.stomp_host, CONF.stomp_port)

    def reconnect(self):
        LOG.warning('Reconnecting to message broker...')
        try:
            self.conn = stomp.Connection(
                [(CONF.stomp_host, int(CONF.stomp_port))],
                reconnect_sleep_initial=_RECONNECT_SLEEP_INITIAL,
                reconnect_sleep_increase=_RECONNECT_SLEEP_INCREASE,
                reconnect_sleep_max=_RECONNECT_SLEEP_MAX,
                reconnect_attempts_max=_RECONNECT_ATTEMPTS_MAX
            )
            if self.callback:
                self.conn.set_listener('', self.callback)
            self.conn.start()
            self.conn.connect(wait=self.wait)
        except Exception, e:
            LOG.error('Could not reconnect to broker %s:%s : %s', CONF.stomp_host, CONF.stomp_port, e)
            return

        LOG.info('Reconnected to broker %s:%s', CONF.stomp_host, CONF.stomp_port)

    def subscribe(self, destination=None, ack='auto'):

        self.destination = destination or CONF.inbound_queue
        self.conn.subscribe(destination=self.destination, ack=ack)

    def send(self, msg, destination=None):

        self.destination = destination or CONF.inbound_queue

        LOG.debug('header = %s', msg.get_header())
        LOG.debug('message = %s', msg.get_body())

        LOG.info('Send %s %s to %s', msg.get_type(), msg.get_id(), self.destination)
        try:
            self.conn.send(message=json.dumps(msg.get_body(), cls=DateEncoder), headers=msg.get_header(),
                           destination=self.destination)
        except exception.NotConnectedException, e:
            LOG.error('Could not send message to broker %s:%s : %s', CONF.stomp_host, CONF.stomp_port, e)
            return
        LOG.info('Message sent to broker %s:%s', CONF.stomp_host, CONF.stomp_port)

    def disconnect(self):
        if self.is_connected():
            LOG.info('Disconnecting from broker %s:%s', CONF.stomp_host, CONF.stomp_port)
            self.conn.disconnect()
        LOG.info('Disconnected!')

    def is_connected(self):
        return self.conn.is_connected()


class MessageHandler(ConnectionListener):
    """
    A generic message handler class.

    Usage: Subclass the MessageHandler class and override the on_message() method
    """
    def on_connecting(self, host_and_port):
        LOG.info('Connecting to %s', host_and_port)

    def on_connected(self, headers, body):
        LOG.info('Connected to %s %s', headers, body)

    def on_disconnected(self):
        LOG.error('Connection to messaging server has been lost.')

    def on_message(self, headers, body):
        LOG.info("Received message %s %s", headers, body)

    def on_receipt(self, headers, body):
        LOG.debug('Receipt received %s %s', headers, body)

    def on_error(self, headers, body):
        LOG.error('Error %s %s', headers, body)

    def on_send(self, headers, body):
        LOG.debug('Sending message %s %s', headers, body)

