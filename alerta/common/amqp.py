
import sys
import json

from kombu import BrokerConnection, Exchange, Queue, Producer, Consumer
from kombu.mixins import ConsumerMixin
# from kombu.utils.debug import setup_logging

from alerta.common import log as logging
from alerta.common import config
from alerta.common.utils import DateEncoder

LOG = logging.getLogger(__name__)
CONF = config.CONF


class Messaging(object):

    amqp_opts = {
        'amqp_queue': 'alerts',
        'amqp_topic': 'notify',
        'amqp_url': 'amqp://guest:guest@localhost:5672//',  # RabbitMQ
        # 'amqp_url': 'mongodb://localhost:27017/kombu',    # MongoDB
        # 'amqp_url': 'redis://localhost:6379/',            # Redis
    }

    def __init__(self):

        config.register_opts(Messaging.amqp_opts)

        self.connection = None
        self.channel = None
        self.connect()

    def connect(self):

        if not CONF.amqp_url:
            return

        self.connection = BrokerConnection(CONF.amqp_url)
        try:
            self.connection.connect()
        except Exception as e:
            LOG.error('Failed to connect to AMQP transport %s: %s', CONF.amqp_url, e)
            sys.exit(1)
        self.channel = self.connection.channel()

        LOG.info('Connected to broker %s', CONF.amqp_url)

    def disconnect(self):

        return self.connection.release()

    def is_connected(self):

        return self.connection.connected


class DirectPublisher(object):

    def __init__(self, channel, name=None):

        config.register_opts(Messaging.amqp_opts)

        self.channel = channel
        self.exchange_name = name or CONF.amqp_queue

        self.exchange = Exchange(name=self.exchange_name, type='direct', channel=self.channel, durable=True)
        self.producer = Producer(exchange=self.exchange, channel=self.channel, serializer='json')

        LOG.info('Configured direct publisher on queue %s', CONF.amqp_queue)

    def send(self, msg):

        if not self.channel:
            return

        self.producer.publish(json.dumps(msg.get_body(), cls=DateEncoder), exchange=self.exchange,
                              serializer='json', declare=[self.exchange], routing_key=self.exchange_name)

        LOG.info('Message sent to exchange "%s"', self.exchange_name)


class FanoutPublisher(object):

    def __init__(self, channel, name=None):

        config.register_opts(Messaging.amqp_opts)

        self.channel = channel
        self.exchange_name = name or CONF.amqp_topic

        self.exchange = Exchange(name=self.exchange_name, type='fanout', channel=self.channel)
        self.producer = Producer(exchange=self.exchange, channel=self.channel, serializer='json')

        LOG.info('Configured fanout publisher on topic "%s"', CONF.amqp_topic)

    def send(self, msg):

        if not self.channel:
            return

        self.producer.publish(json.dumps(msg.get_body(), cls=DateEncoder), exchange=self.exchange,
                              serializer='json', declare=[self.exchange])

        LOG.info('Message sent to exchange "%s"', self.exchange_name)


class DirectConsumer(ConsumerMixin):

    config.register_opts(Messaging.amqp_opts)

    def __init__(self, connection):

        self.connection = connection
        self.channel = self.connection.channel()
        self.exchange = Exchange(CONF.amqp_queue, 'direct', channel=self.channel, durable=True)
        self.queue = Queue(CONF.amqp_queue, exchange=self.exchange, routing_key=CONF.amqp_queue, channel=self.channel)

        LOG.info('Configured direct consumer on queue %s', CONF.amqp_queue)

    def get_consumers(self, Consumer, channel):

        return [
            Consumer(queues=[self.queue], callbacks=[self.on_message])
        ]

    def on_message(self, body, message):
        LOG.debug('Received queue message: {0!r}'.format(body))
        message.ack()


class FanoutConsumer(ConsumerMixin):

    config.register_opts(Messaging.amqp_opts)

    def __init__(self, connection):

        self.connection = connection
        self.channel = self.connection.channel()
        self.exchange = Exchange(CONF.amqp_topic, 'fanout', channel=self.channel, durable=True)
        self.queue = Queue('', exchange=self.exchange, routing_key='', channel=self.channel, exclusive=True)

        LOG.info('Configured fanout consumer on topic "%s"', CONF.amqp_topic)

    def get_consumers(self, Consumer, channel):

        return [
            Consumer(queues=[self.queue], callbacks=[self.on_message])
        ]

    def on_message(self, body, message):
        LOG.debug('Received topic message: {0!r}'.format(body))
        message.ack()
