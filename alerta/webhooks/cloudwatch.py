
import json
from datetime import datetime

from flask import request, g, jsonify
from flask_cors import cross_origin

from alerta.auth.utils import permission
from alerta.exceptions import ApiError, RejectException
from alerta.models.alert import Alert
from alerta.utils.api import process_alert, add_remote_ip
from . import webhooks


def cw_state_to_severity(state):

    if state == 'ALARM':
        return 'major'
    elif state == 'INSUFFICIENT_DATA':
        return 'warning'
    elif state == 'OK':
        return 'normal'
    else:
        return 'unknown'


def parse_notification(notification):

    notification = json.loads(notification)

    if notification['Type'] == 'SubscriptionConfirmation':

        return Alert(
            resource=notification['TopicArn'],
            event=notification['Type'],
            environment='Production',
            severity='informational',
            service=['Unknown'],
            group='AWS/CloudWatch',
            text='%s <a href="%s" target="_blank">SubscribeURL</a>' % (notification['Message'], notification['SubscribeURL']),
            origin=notification['TopicArn'],
            event_type='cloudwatchAlarm',
            create_time=datetime.strptime(notification['Timestamp'], '%Y-%m-%dT%H:%M:%S.%fZ'),
            raw_data=notification,
        )

    elif notification['Type'] == 'Notification':

        alarm = json.loads(notification['Message'])

        if 'Trigger' not in alarm:
            raise ValueError("SNS message is not a Cloudwatch notification")

        return Alert(
            resource='%s:%s' % (alarm['Trigger']['Dimensions'][0]['name'], alarm['Trigger']['Dimensions'][0]['value']),
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


@webhooks.route('/webhooks/cloudwatch', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission('write:webhooks')
def cloudwatch():

    try:
        incomingAlert = parse_notification(request.data)
    except ValueError as e:
        raise ApiError(str(e), 400)

    if g.get('customer', None):
        incomingAlert.customer = g.get('customer')

    add_remote_ip(request, incomingAlert)

    try:
        alert = process_alert(incomingAlert)
    except RejectException as e:
        raise ApiError(str(e), 403)
    except Exception as e:
        raise ApiError(str(e), 500)

    if alert:
        return jsonify(status="ok", id=alert.id, alert=alert.serialize), 201
    else:
        raise ApiError("insert or update of cloudwatch alarm failed", 500)
