
import sys
import json
import datetime

import boto.sqs
from boto.sqs.message import RawMessage

from alerta.common import config
from alerta.common import log as logging
from alerta.common.daemon import Daemon
from alerta.common.alert import Alert
from alerta.common import severity_code
from alerta.common.heartbeat import Heartbeat
from alerta.common.dedup import DeDup
from alerta.common.mq import Messaging, MessageHandler
from alerta.common.graphite import StatsD

Version = '2.0.2'

LOG = logging.getLogger(__name__)
CONF = config.CONF


class CloudWatchMessage(MessageHandler):

    def __init__(self, mq):
        self.mq = mq
        MessageHandler.__init__(self)

    def on_disconnected(self):
        self.mq.reconnect()


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
        self.mq = Messaging()
        self.mq.connect(callback=CloudWatchMessage(self.mq))

        self.dedup = DeDup(by_value=True)

        try:
            sqs = boto.sqs.connect_to_region(
                CONF.cloudwatch_sqs_region,
                aws_access_key_id=CONF.cloudwatch_access_key,
                aws_secret_access_key=CONF.cloudwatch_secret_key
            )
        except boto.exception.SQSError, e:
            LOG.error('SQS API call failed: %s', e)
            sys.exit(1)

        try:
            q = sqs.create_queue(CONF.cloudwatch_sqs_queue)
            q.set_message_class(RawMessage)
        except boto.exception.SQSError, e:
            LOG.error('SQS queue error: %s', e)
            sys.exit(1)

        while not self.shuttingdown:
            try:
                try:
                    m = q.read(wait_time_seconds=20)
                except boto.exception.SQSError, e:
                    LOG.warning('Could not read from queue: %s', e)

                if m:
                    message = m.get_body()
                    cloudwatchAlert = self.parse_notification(message)
                    if self.dedup.is_send(cloudwatchAlert):
                        self.mq.send(cloudwatchAlert)
                    q.delete_message(m)

                LOG.debug('Send heartbeat...')
                heartbeat = Heartbeat(version=Version)
                self.mq.send(heartbeat)

            except (KeyboardInterrupt, SystemExit):
                self.shuttingdown = True

        LOG.info('Shutdown request received...')
        self.running = False

        LOG.info('Disconnecting from message broker...')
        self.mq.disconnect()

    def parse_notification(self, message):

        LOG.debug('Parsing CloudWatch notification message...')

        notification = json.loads(message)
        if 'Message' in notification:
            alarm = json.loads(notification['Message'])
        else:
            return

        # Defaults
        alertid = notification['MessageId']
        resource = alarm['Trigger']['Dimensions'][0]['value']
        event = alarm['AlarmName']
        severity = self.cw_state_to_severity(alarm['NewStateValue'])
        previous_severity = self.cw_state_to_severity(alarm['OldStateValue'])
        group = 'CloudWatch'
        value = alarm['NewStateValue']
        text = alarm['AlarmDescription']
        environment = ['INFRA']
        service = [alarm['AWSAccountId']]  # XXX - use transform_alert() to map AWSAccountId to a useful name
        tags = [alarm['Region']]
        correlate = list()
        origin = notification['TopicArn']
        timeout = None
        threshold_info = alarm['NewStateReason']
        summary = notification['Subject']
        create_time = datetime.datetime.strptime(notification['Timestamp'], '%Y-%m-%dT%H:%M:%S.%fZ')
        raw_data = notification['Message']

        cloudwatchAlert = Alert(
            alertid=alertid,
            resource=resource,
            event=event,
            correlate=correlate,
            group=group,
            value=value,
            severity=severity,
            previous_severity=previous_severity,
            environment=environment,
            service=service,
            text=text,
            event_type='cloudwatchAlarm',
            tags=tags,
            origin=origin,
            timeout=timeout,
            threshold_info=threshold_info,
            summary=summary,
            create_time=create_time,
            raw_data=raw_data,
        )

        suppress = cloudwatchAlert.transform_alert()
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

