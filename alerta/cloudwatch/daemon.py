
import sys
import json
import datetime

import boto.sqs
from boto.sqs.message import RawMessage

from alerta.common import config, syslog
from alerta.common import log as logging
from alerta.common.daemon import Daemon
from alerta.common.alert import Alert
from alerta.common import status_code, severity_code
from alerta.common.heartbeat import Heartbeat
from alerta.common.dedup import DeDup
from alerta.common.mq import Messaging, MessageHandler
from alerta.common.graphite import StatsD

Version = '2.0.0'

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
        'cloudwatch_sqs_queue': 'alerta',
        'cloudwatch_access_key': 'AKIAIAK2IYG7WDX5L6VA',
        'cloudwatch_secret_key': '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'
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

        q = sqs.create_queue(CONF.cloudwatch_sqs_queue)
        q.set_message_class(RawMessage)

        while not self.shuttingdown:
            try:
                m = q.read(wait_time_seconds=20)

                if m:
                    message = m.get_body()
                    cloudwatchAlert = self.parse_notification(message)
                    if self.dedup.is_send(cloudwatchAlert):
                        self.mq.send(cloudwatchAlert)
                    # q.delete_message(m)

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

        LOG.debug('Parsing CloudWatch Notification message...')

        # {
        #   "Type" : "Notification",
        #   "MessageId" : "29ecfcf6-7bd2-5cc9-bfdd-b7a75b3999a0",
        #   "TopicArn" : "arn:aws:sns:eu-west-1:496780030265:alerta",
        #   "Subject" : "ALARM: \"awselb-lb001-High-Unhealthy-Hosts\" in EU - Ireland",
        #   "Message" : "{\"AlarmName\":\"awselb-lb001-High-Unhealthy-Hosts\",\"AlarmDescription\":\"Created from AWS Console\",\"AWSAccountId\":\"496780030265\",\"NewStateValue\":\"ALARM\",\"NewStateReason\":\"Threshold Crossed: 1 datapoint (1.0) was greater than or equal to the threshold (0.0).\",\"StateChangeTime\":\"2014-01-15T23:50:03.190+0000\",\"Region\":\"EU - Ireland\",\"OldStateValue\":\"INSUFFICIENT_DATA\",\"Trigger\":{\"MetricName\":\"UnHealthyHostCount\",\"Namespace\":\"AWS/ELB\",\"Statistic\":\"SUM\",\"Unit\":null,\"Dimensions\":[{\"name\":\"LoadBalancerName\",\"value\":\"lb001\"}],\"Period\":60,\"EvaluationPeriods\":1,\"ComparisonOperator\":\"GreaterThanOrEqualToThreshold\",\"Threshold\":0.0}}",
        #   "Timestamp" : "2014-01-15T23:50:03.242Z",
        #   "SignatureVersion" : "1",
        #   "Signature" : "TlJumlRUe9ia1/wxpQwq2eBMXLFgd40057UgUDfShUn4qGYaNFNhkPvL+k6p5yZpjTT7TQUYLXQOrvphRgZSg7/+jEvw5EGOT27t1BYHqpLBolEUgg6xBZD/chWImpGJErotjvrIMaCxQR/Bxb8rYU420LsexdpWQCe4nvUr8A6i/gaevGb9YwcYQtmf/vPLXiwDMtLGAeuhnuyYy1xuOF2gKNfxhLKYb2i/+cAwJCEaBOO9hlKtyGA5R0QZ1PN4dy2Gr8VWs6p0/VUzkfX3gREEsoEk1laKaQ7868Y6Uu5FQcVQqooy3YtgkkP7XUoHxn4Fe/7uHIlfXKK+Oyv17A==",
        #   "SigningCertURL" : "https://sns.eu-west-1.amazonaws.com/SimpleNotificationService-e372f8ca30337fdb084e8ac449342c77.pem",
        #   "UnsubscribeURL" : "https://sns.eu-west-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:eu-west-1:496780030265:alerta:ddea6c9c-ee0a-4972-bb41-9f4660e9990b"
        # }

        alarm_ex = {u'NewStateReason': u'Threshold Crossed: 1 datapoint (1.0) was greater than or equal to the threshold (0.0).',
             u'Region': u'EU - Ireland',
             u'AlarmDescription': u'Created from AWS Console',
             u'NewStateValue': u'ALARM',
             u'Trigger': {u'EvaluationPeriods': 1, u'Dimensions': [{u'name': u'LoadBalancerName', u'value': u'lb001'}],
                          u'Namespace': u'AWS/ELB', u'Period': 60, u'ComparisonOperator': u'GreaterThanOrEqualToThreshold',
                          u'Statistic': u'SUM', u'Threshold': 0.0, u'Unit': None, u'MetricName': u'UnHealthyHostCount'},
             u'OldStateValue': u'INSUFFICIENT_DATA',
             u'AlarmName': u'awselb-lb001-High-Unhealthy-Hosts',
             u'StateChangeTime': u'2014-01-15T23:50:03.190+0000',
             u'AWSAccountId': u'496780030265'}

        notification = json.loads(message)
        if 'Message' in notification:
            alarm = json.loads(notification['Message'])

        # Defaults
        alertid = notification['MessageId']
        resource = alarm['Trigger']['Dimensions'][0]['value']
        event = alarm['AlarmName']
        if alarm['NewStateValue'] == 'ALARM':
            severity = severity_code.MAJOR
        elif alarm['NewStateValue'] == 'INSUFFICIENT_DATA':
            severity = severity_code.WARNING
        elif alarm['NewStateValue'] == 'OK':
            severity = severity_code.NORMAL
        else:
            severity = severity_code.UNKNOWN
        group = 'CloudWatch'
        value = alarm['NewStateValue']
        text = alarm['AlarmDescription']
        environment = ['INFRA']
        service = ['AWS']
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
        print cloudwatchAlert

        suppress = cloudwatchAlert.transform_alert()
        if suppress:
            LOG.info('Suppressing %s alert', event)
            LOG.debug('%s', cloudwatchAlert)
            return

        return cloudwatchAlert

