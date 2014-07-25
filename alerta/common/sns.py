
import sys

import boto.sns
import boto.exception

from alerta import settings
from alerta.common import log as logging

LOG = logging.getLogger(__name__)


class SimpleNotificationService(object):

    def __init__(self):

        try:
            self.connection = boto.sns.connect_to_region(
                region_name=settings.REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
        except Exception, e:
            LOG.error('Error connecting to SNS topic %s: %s', settings.TOPIC, e)
            sys.exit(1)

        if not self.connection:
            LOG.error('Failed to connect to SNS topic %s - check AWS authentication settings and region', settings.TOPIC)
            sys.exit(1)

        LOG.info('Notification service connected to %s', self.connection)

    def disconnect(self):

        pass

    def is_connected(self):

        return self.connection is not None


class TopicPublisher(object):

    def __init__(self, sns):

        self.connection = sns.connection

        try:
            response = self.connection.create_topic(settings.TOPIC)
        except boto.exception.BotoServerError as e:
            LOG.error('Error creating SNS topic %s: %s', settings.TOPIC, e)
            sys.exit(1)

        try:
            self.topic_arn = response['CreateTopicResponse']['CreateTopicResult']['TopicArn']
        except KeyError:
            LOG.error('Failed to get SNS TopicArn for %s', settings.TOPIC)
            sys.exit(1)

        LOG.info('Configured SNS publisher on topic "%s"', self.topic_arn)

    def send(self, msg):

        LOG.info('Sending message %s to SNS topic "%s"', msg.get_id(), self.topic_arn)
        LOG.debug('Message: %s', msg.get_body())

        response = self.connection.publish(topic=self.topic_arn, message=msg.get_body())
        LOG.debug('Response: %s', response)
