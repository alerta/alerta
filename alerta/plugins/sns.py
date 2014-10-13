
import boto.sns
import boto.exception

from alerta.app import app
from alerta.plugins import PluginBase

LOG = app.logger


class SnsTopicPublisher(PluginBase):

    def __init__(self):

        try:
            self.connection = boto.sns.connect_to_region(
                region_name=app.config['AWS_REGION'],
                aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'],
                aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY']
            )
        except Exception, e:
            LOG.error('Error connecting to SNS topic %s: %s', app.config['AWS_SNS_TOPIC'], e)
            raise RuntimeError

        if not self.connection:
            LOG.error('Failed to connect to SNS topic %s - check AWS credentials and region', app.config['AWS_SNS_TOPIC'])
            raise RuntimeError

        try:
            response = self.connection.create_topic(app.config['AWS_SNS_TOPIC'])
        except boto.exception.BotoServerError as e:
            LOG.error('Error creating SNS topic %s: %s', app.config['AWS_SNS_TOPIC'], e)
            raise RuntimeError

        try:
            self.topic_arn = response['CreateTopicResponse']['CreateTopicResult']['TopicArn']
        except KeyError:
            LOG.error('Failed to get SNS TopicArn for %s', app.config['AWS_SNS_TOPIC'])
            raise RuntimeError

        LOG.info('Configured SNS publisher on topic "%s"', self.topic_arn)

    def pre_receive(self, alert):

        return alert

    def post_receive(self, alert):

        LOG.info('Sending message %s to SNS topic "%s"', alert.get_id(), self.topic_arn)
        LOG.debug('Message: %s', alert.get_body())

        response = self.connection.publish(topic=self.topic_arn, message=alert.get_body())
        LOG.debug('Response: %s', response)
