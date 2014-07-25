
import sys

from kombu import BrokerConnection, Exchange, Queue, Producer
from kombu.mixins import ConsumerMixin
from kombu.utils.debug import setup_logging

from alerta import settings
from alerta.common import log as logging

LOG = logging.getLogger(__name__)


class Messaging(object):

    def __init__(self):

        if settings.DEBUG:
            setup_logging(loglevel='DEBUG', loggers=[''])

        self.connection = None
        self.connect()

    def connect(self):

        if not settings.AMQP_URL:
            return

        self.connection = BrokerConnection(settings.AMQP_URL)
        try:
            self.connection.connect()
        except Exception as e:
            LOG.error('Failed to connect to AMQP transport %s: %s', settings.AMQP_URL, e)
            sys.exit(1)

        LOG.info('Connected to broker %s', settings.AMQP_URL)

    def disconnect(self):

        return self.connection.release()

    def is_connected(self):

        return self.connection.connected


class FanoutPublisher(object):

    def __init__(self, connection):

        self.channel = connection.channel()
        self.exchange_name = settings.TOPIC

        self.exchange = Exchange(name=self.exchange_name, type='fanout', channel=self.channel)
        self.producer = Producer(exchange=self.exchange, channel=self.channel)

        LOG.info('Configured fanout publisher on topic "%s"', settings.TOPIC)

    def send(self, msg):

        LOG.info('Sending message %s to AMQP topic "%s"', msg.get_id(), settings.TOPIC)
        LOG.debug('Message: %s', msg.get_body())

        self.producer.publish(msg.get_body(), declare=[self.exchange], retry=True)


class DirectConsumer(ConsumerMixin):

    def __init__(self, connection):

        self.channel = connection.channel()
        self.exchange = Exchange(settings.QUEUE, type='direct', channel=self.channel, durable=True)
        self.queue = Queue(settings.QUEUE, exchange=self.exchange, routing_key=settings.QUEUE, channel=self.channel)

        LOG.info('Configured direct consumer on queue %s', settings.QUEUE)

    def get_consumers(self, Consumer, channel):

        return [
            Consumer(queues=[self.queue], callbacks=[self.on_message])
        ]

    def on_message(self, body, message):

        LOG.debug('Received queue message: {0!r}'.format(body))
        message.ack()
