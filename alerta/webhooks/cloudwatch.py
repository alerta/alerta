
import json
from datetime import datetime
from typing import Any, Dict

from alerta.models.alert import Alert

from . import WebhookBase

JSON = Dict[str, Any]


class CloudWatchWebhook(WebhookBase):
    """
    Amazon CloudWatch notifications via SNS HTTPS endpoint subscription
    See https://docs.aws.amazon.com/sns/latest/dg/sns-http-https-endpoint-as-subscriber.html
    """

    @staticmethod
    def cw_state_to_severity(state: str) -> str:
        if state == 'ALARM':
            return 'major'
        elif state == 'INSUFFICIENT_DATA':
            return 'warning'
        elif state == 'OK':
            return 'normal'
        else:
            return 'unknown'

    def incoming(self, query_string, payload):
        notification = json.loads(payload)

        if notification['Type'] == 'SubscriptionConfirmation':
            return Alert(
                resource=notification['TopicArn'],
                event=notification['Type'],
                environment='Production',
                severity='informational',
                service=['Unknown'],
                group='AWS/CloudWatch',
                text='{} <a href="{}" target="_blank">SubscribeURL</a>'.format(
                    notification['Message'], notification['SubscribeURL']),
                origin=notification['TopicArn'],
                event_type='cloudwatchAlarm',
                create_time=datetime.strptime(notification['Timestamp'], '%Y-%m-%dT%H:%M:%S.%fZ'),
                raw_data=notification
            )

        elif notification['Type'] == 'Notification':
            alarm = json.loads(notification['Message'])

            if 'Trigger' not in alarm:
                raise ValueError('SNS message is not a Cloudwatch notification')

            return Alert(
                resource='{}:{}'.format(alarm['Trigger']['Dimensions'][0]['name'],
                                        alarm['Trigger']['Dimensions'][0]['value']),
                event=alarm['AlarmName'],
                environment='Production',
                severity=self.cw_state_to_severity(alarm['NewStateValue']),
                service=[alarm['AWSAccountId']],
                group=alarm['Trigger']['Namespace'],
                value=alarm['NewStateValue'],
                text=alarm['AlarmDescription'],
                tags=[alarm['Region']],
                attributes={
                    'incidentKey': alarm['AlarmName'],
                    'thresholdInfo': alarm['Trigger']
                },
                origin=notification['TopicArn'],
                event_type='cloudwatchAlarm',
                create_time=datetime.strptime(notification['Timestamp'], '%Y-%m-%dT%H:%M:%S.%fZ'),
                raw_data=alarm
            )
        else:
            raise ValueError('No SNS notification in payload')
