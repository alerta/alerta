
import sys
import json
import time
import datetime

import boto.sqs
from boto.sqs.message import RawMessage
from boto import exception

from alerta.common import config
from alerta.common import log as logging
from alerta.common.daemon import Daemon
from alerta.common.alert import Alert
from alerta.common.heartbeat import Heartbeat
from alerta.common import severity_code
from alerta.common.transform import Transformers
from alerta.common.dedup import DeDup
from alerta.common.api import ApiClient
from alerta.common.graphite import StatsD

__version__ = '3.0.3'

LOG = logging.getLogger(__name__)
CONF = config.CONF


class CloudWatchDaemon(Daemon):

    cloudwatch_opts = {
        'cloudwatch_sqs_region': 'eu-west-1',
        'cloudwatch_sqs_queue': 'cloudwatch-to-alerta',
        'cloudwatch_access_key': '022QF06E7MXBSAMPLE',
        'cloudwatch_secret_key': ''
    }

    def __init__(self, prog, **kwargs):

        config.register_opts(CloudWatchDaemon.cloudwatch_opts)

        Daemon.__init__(self, prog, kwargs)

    def run(self):

        self.running = True

        self.statsd = StatsD()  # graphite metrics

        # Connect to message queue
        self.api = ApiClient()

        self.dedup = DeDup(by_value=True)

        LOG.info('Connecting to SQS queue %s', CONF.cloudwatch_sqs_queue)
        try:
            connection = boto.sqs.connect_to_region(
                CONF.cloudwatch_sqs_region,
                aws_access_key_id=CONF.cloudwatch_access_key,
                aws_secret_access_key=CONF.cloudwatch_secret_key
            )
        except boto.exception.SQSError, e:
            LOG.error('SQS API call failed: %s', e)
            sys.exit(1)

        try:
            sqs = connection.create_queue(CONF.cloudwatch_sqs_queue)
            sqs.set_message_class(RawMessage)
        except boto.exception.SQSError, e:
            LOG.error('SQS queue error: %s', e)
            sys.exit(1)

        while not self.shuttingdown:
            try:
                LOG.info('Waiting for CloudWatch alarms...')
                try:
                    message = sqs.read(wait_time_seconds=20)
                except boto.exception.SQSError, e:
                    LOG.warning('Could not read from queue: %s', e)
                    time.sleep(20)
                    continue

                if message:
                    body = message.get_body()
                    cloudwatchAlert = self.parse_notification(body)
                    if self.dedup.is_send(cloudwatchAlert):
                        try:
                            self.api.send(cloudwatchAlert)
                        except Exception, e:
                            LOG.warning('Failed to send alert: %s', e)
                    sqs.delete_message(message)

                LOG.debug('Send heartbeat...')
                heartbeat = Heartbeat(tags=[__version__])
                try:
                    self.api.send(heartbeat)
                except Exception, e:
                    LOG.warning('Failed to send heartbeat: %s', e)

            except (KeyboardInterrupt, SystemExit):
                self.shuttingdown = True

        LOG.info('Shutdown request received...')
        self.running = False

    def parse_notification(self, message):

        LOG.debug('Parsing CloudWatch notification message...')

        notification = json.loads(message)
        if 'Message' in notification:
            alarm = notification['Message']
        else:
            return

        if 'Trigger' not in alarm:
            return

        # Defaults
        resource = alarm['Trigger']['Dimensions'][0]['value']
        event = alarm['AlarmName']
        severity = self.cw_state_to_severity(alarm['NewStateValue'])
        group = 'CloudWatch'
        value = alarm['NewStateValue']
        text = alarm['AlarmDescription']
        environment = ['INFRA']
        service = [alarm['AWSAccountId']]
        tags = [notification['MessageId'], alarm['Region']]
        correlate = list()
        origin = [notification['TopicArn']]
        timeout = None
        threshold_info = alarm['NewStateReason']
        more_info = notification['Subject']
        create_time = datetime.datetime.strptime(notification['Timestamp'], '%Y-%m-%dT%H:%M:%S.%fZ')
        raw_data = notification['Message']

        cloudwatchAlert = Alert(
            resource=resource,
            event=event,
            correlate=correlate,
            group=group,
            value=value,
            severity=severity,
            environment=environment,
            service=service,
            text=text,
            event_type='cloudwatchAlarm',
            tags=tags,
            attributes={
                'thresholdInfo': threshold_info,
                'moreInfo': more_info
            },
            origin=origin,
            timeout=timeout,
            create_time=create_time,
            raw_data=raw_data,
        )

        suppress = Transformers.normalise_alert(cloudwatchAlert)
        if suppress:
            LOG.info('Suppressing %s alert', event)
            LOG.debug('%s', cloudwatchAlert)
            return

        return cloudwatchAlert

    @staticmethod
    def cw_state_to_severity(state):

        if state == 'ALARM':
            return severity_code.MAJOR
        elif state == 'INSUFFICIENT_DATA':
            return severity_code.WARNING
        elif state == 'OK':
            return severity_code.NORMAL
        else:
            return severity_code.UNKNOWN

