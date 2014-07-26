
import logging

from kombu import BrokerConnection, Exchange, Producer
from kombu.utils.debug import setup_logging

from alerta import settings

LOG = logging.getLogger(__name__)


class FanoutPublisher(object):

    def __init__(self):

        if settings.DEBUG:
            setup_logging(loglevel='DEBUG', loggers=[''])

        self.connection = BrokerConnection(settings.AMQP_URL)
        try:
            self.connection.connect()
        except Exception as e:
            LOG.error('Failed to connect to AMQP transport %s: %s', settings.AMQP_URL, e)
            raise RuntimeError

        self.channel = self.connection.channel()
        self.exchange_name = settings.AMQP_TOPIC

        self.exchange = Exchange(name=self.exchange_name, type='fanout', channel=self.channel)
        self.producer = Producer(exchange=self.exchange, channel=self.channel)

        LOG.info('Configured fanout publisher on topic "%s"', settings.AMQP_TOPIC)

    def send(self, msg):

        LOG.info('Sending message %s to AMQP topic "%s"', msg.get_id(), settings.AMQP_TOPIC)
        LOG.debug('Message: %s', msg.get_body())

        self.producer.publish(msg.get_body(), declare=[self.exchange], retry=True)
