
import sys

import boto.sns

from alerta.common import log as logging
from alerta.common import config

LOG = logging.getLogger(__name__)
CONF = config.CONF


class NotificationService(object):

    sns_opts = {
        'output_topic': 'notify',
        'aws_access_key_id': 'AWS_ACCESS_KEY_ID',
        'aws_secret_access_key': 'AWS_SECRET_ACCESS_KEY',
        'sns_region': 'eu-west-1',
    }

    def __init__(self):

        config.register_opts(NotificationService.sns_opts)

        self.connection = boto.sns.connect_to_region(
            region_name=CONF.sns_region,
            aws_access_key_id=CONF.aws_access_key_id,
            aws_secret_access_key=CONF.aws_secret_access_key
        )
        LOG.info('Notification service connected to %s', self.connection)

    def disconnect(self):

        pass

    def is_connected(self):

        return self.connection is not None


class TopicPublisher(object):

    def __init__(self, sns):

        self.connection = sns.connection

        response = self.connection.create_topic(CONF.output_topic)

        try:
            self.topic_arn = response['CreateTopicResponse']['CreateTopicResult']['TopicArn']
        except KeyError:
            LOG.error('Failed to create SNS topic %s', CONF.output_topic)
            sys.exit(1)

        LOG.info('Configured SNS publisher on topic "%s"', self.topic_arn)

    def send(self, msg):

        self.connection.publish(topic=self.topic_arn, message=msg.get_body())

        LOG.info('Message sent to SNS topic "%s"', self.topic_arn)
        LOG.debug('Message: %s', msg.get_body())

