
from kombu import BrokerConnection, Exchange, Producer
from kombu.utils.debug import setup_logging

from alerta.app import app
from alerta.plugins import PluginBase

LOG = app.logger


class FanoutPublisher(PluginBase):

    def __init__(self):

        if app.debug:
            setup_logging(loglevel='DEBUG', loggers=[''])

        self.connection = BrokerConnection(app.config['AMQP_URL'])
        try:
            self.connection.connect()
        except Exception as e:
            LOG.error('Failed to connect to AMQP transport %s: %s', app.config['AMQP_URL'], e)
            raise RuntimeError

        self.channel = self.connection.channel()
        self.exchange_name = app.config['AMQP_TOPIC']

        self.exchange = Exchange(name=self.exchange_name, type='fanout', channel=self.channel)
        self.producer = Producer(exchange=self.exchange, channel=self.channel)

        LOG.info('Configured fanout publisher on topic "%s"', app.config['AMQP_TOPIC'])

    def pre_receive(self, alert):

        return alert

    def post_receive(self, alert):

        LOG.info('Sending message %s to AMQP topic "%s"', alert.get_id(), app.config['AMQP_TOPIC'])
        LOG.debug('Message: %s', alert.get_body())

        self.producer.publish(alert.get_body(), declare=[self.exchange], retry=True)
