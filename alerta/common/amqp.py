
import sys

from kombu import BrokerConnection, Exchange, Queue, Producer
from kombu.mixins import ConsumerMixin
from kombu.utils.debug import setup_logging

from alerta.common import log as logging
from alerta.common import config

LOG = logging.getLogger(__name__)
CONF = config.CONF


class Messaging(object):

    amqp_opts = {
        'amqp_queue': '',                                   # do not send to queue by default
        'amqp_topic': 'notify',
        'amqp_url': 'amqp://guest:guest@localhost:5672//',  # RabbitMQ
        # 'amqp_url': 'mongodb://localhost:27017/kombu',    # MongoDB
        # 'amqp_url': 'redis://localhost:6379/',            # Redis
        # 'amqp_url': 'sqs://ACCESS_KEY:SECRET_KEY@'        # AWS SQS (must define amqp_queue)
        # 'amqp_sqs_region': 'eu-west-1'                    # required if SQS is used
    }

    def __init__(self):

        config.register_opts(Messaging.amqp_opts)

        if CONF.debug:
            setup_logging(loglevel='DEBUG', loggers=[''])

        self.connection = None
        self.connect()

    def connect(self):

        if not CONF.amqp_url:
            return

        if CONF.amqp_sqs_region:
            transport_options = {'region': CONF.amqp_sqs_region}
        else:
            transport_options = {}

        self.connection = BrokerConnection(
            CONF.amqp_url,
            transport_options=transport_options
        )
        try:
            self.connection.connect()
        except Exception as e:
            LOG.error('Failed to connect to AMQP transport %s: %s', CONF.amqp_url, e)
            sys.exit(1)

        LOG.info('Connected to broker %s', CONF.amqp_url)

    def disconnect(self):

        return self.connection.release()

    def is_connected(self):

        return self.connection.connected


class DirectPublisher(object):

    def __init__(self, connection):

        config.register_opts(Messaging.amqp_opts)

        self.queue = connection.SimpleQueue(CONF.amqp_queue)

        LOG.info('Configured direct publisher on queue "%s"', CONF.amqp_queue)

    def send(self, msg):

        self.queue.put(msg.get_body())

        LOG.info('Message sent to queue "%s"', CONF.amqp_queue)


class FanoutPublisher(object):

    def __init__(self, connection):

        config.register_opts(Messaging.amqp_opts)

        self.channel = connection.channel()
        self.exchange_name = CONF.amqp_topic

        self.exchange = Exchange(name=self.exchange_name, type='fanout', channel=self.channel)
        self.producer = Producer(exchange=self.exchange, channel=self.channel)

        LOG.info('Configured fanout publisher on topic "%s"', CONF.amqp_topic)

    def send(self, msg):

        self.producer.publish(msg.get_body(), declare=[self.exchange], retry=True)

        LOG.info('Message sent to topic "%s"', CONF.amqp_topic)


class DirectConsumer(ConsumerMixin):

    config.register_opts(Messaging.amqp_opts)

    def __init__(self, connection):

        self.channel = connection.channel()
        self.exchange = Exchange(CONF.amqp_queue, type='direct', channel=self.channel, durable=True)
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

        self.channel = connection.channel()
        self.exchange = Exchange(CONF.amqp_topic, type='fanout', channel=self.channel, durable=True)
        self.queue = Queue('', exchange=self.exchange, routing_key='', channel=self.channel, exclusive=True)

        LOG.info('Configured fanout consumer on topic "%s"', CONF.amqp_topic)

    def get_consumers(self, Consumer, channel):

        return [
            Consumer(queues=[self.queue], callbacks=[self.on_message])
        ]

    def on_message(self, body, message):

        LOG.debug('Received topic message: {0!r}'.format(body))
        message.ack()
