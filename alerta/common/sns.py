
import sys

import boto.sns
import boto.exception

from alerta.common import log as logging
from alerta.common import config

LOG = logging.getLogger(__name__)
CONF = config.CONF


class SimpleNotificationService(object):

    sns_opts = {
        'topic': 'notify',                                  # alarm topic
        'aws_access_key_id': 'AWS_ACCESS_KEY_ID',
        'aws_secret_access_key': 'AWS_SECRET_ACCESS_KEY',
        'region': 'eu-west-1',
    }

    def __init__(self):

        config.register_opts(SimpleNotificationService.sns_opts)

        try:
            self.connection = boto.sns.connect_to_region(
                region_name=CONF.region,
                aws_access_key_id=CONF.aws_access_key_id,
                aws_secret_access_key=CONF.aws_secret_access_key
            )
        except Exception, e:
            LOG.error('Error connecting to SNS topic %s: %s', CONF.topic, e)
            sys.exit(1)

        if not self.connection:
            LOG.error('Failed to connect to SNS topic %s - check AWS authentication settings and region', CONF.topic)
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
            response = self.connection.create_topic(CONF.topic)
        except boto.exception.BotoServerError as e:
            LOG.error('Error creating SNS topic %s: %s', CONF.topic, e)
            sys.exit(1)

        try:
            self.topic_arn = response['CreateTopicResponse']['CreateTopicResult']['TopicArn']
        except KeyError:
            LOG.error('Failed to get SNS TopicArn for %s', CONF.topic)
            sys.exit(1)

        LOG.info('Configured SNS publisher on topic "%s"', self.topic_arn)

    def send(self, msg):

        self.connection.publish(topic=self.topic_arn, message=msg.get_body())

        LOG.info('Message sent to SNS topic "%s"', self.topic_arn)
        LOG.debug('Message: %s', msg.get_body())

