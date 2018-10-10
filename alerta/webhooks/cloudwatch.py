
import json
from datetime import datetime
from typing import Any, Dict

from flask import jsonify, request
from flask_cors import cross_origin

from alerta.auth.decorators import permission
from alerta.exceptions import ApiError, RejectException
from alerta.models.alert import Alert
from alerta.utils.api import add_remote_ip, assign_customer, process_alert

from . import webhooks

JSON = Dict[str, Any]


def cw_state_to_severity(state: str) -> str:

    if state == 'ALARM':
        return 'major'
    elif state == 'INSUFFICIENT_DATA':
        return 'warning'
    elif state == 'OK':
        return 'normal'
    else:
        return 'unknown'


def parse_notification(notification: JSON) -> Alert:

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
            raw_data=notification,
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
            severity=cw_state_to_severity(alarm['NewStateValue']),
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
        raise RuntimeWarning('No SNS notification in payload')


@webhooks.route('/webhooks/cloudwatch', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission('write:webhooks')
def cloudwatch():

    try:
        incomingAlert = parse_notification(request.get_json(force=True))
    except ValueError as e:
        raise ApiError(str(e), 400)

    incomingAlert.customer = assign_customer(wanted=incomingAlert.customer)
    add_remote_ip(request, incomingAlert)

    try:
        alert = process_alert(incomingAlert)
    except RejectException as e:
        raise ApiError(str(e), 403)
    except Exception as e:
        raise ApiError(str(e), 500)

    if alert:
        return jsonify(status='ok', id=alert.id, alert=alert.serialize), 201
    else:
        raise ApiError('insert or update of cloudwatch alarm failed', 500)
