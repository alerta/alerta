import json
import datetime

from flask import request
from flask.ext.cors import cross_origin

from alerta.app import app
from alerta.alert import Alert
from alerta.app.utils import jsonify, jsonp, process_alert
from alerta.app.metrics import Timer
from alerta.plugins import RejectException

LOG = app.logger

webhook_timer = Timer('alerts', 'webhook', 'Web hook alerts', 'Total time to process number of web hook alerts')
duplicate_timer = Timer('alerts', 'duplicate', 'Duplicate alerts', 'Total time to process number of duplicate alerts')
correlate_timer = Timer('alerts', 'correlate', 'Correlated alerts', 'Total time to process number of correlated alerts')
create_timer = Timer('alerts', 'create', 'Newly created alerts', 'Total time to process number of new alerts')


def parse_notification(notification):

    notification = json.loads(notification)

    if notification['Type'] == 'SubscriptionConfirmation':

        return Alert(
            resource=notification['TopicArn'],
            event=notification['Type'],
            environment='Production',
            severity='informational',
            service=['Unknown'],
            group='CloudWatch',
            text='%s <a href="%s" target="_blank">SubscribeURL</a>' % (notification['Message'], notification['SubscribeURL']),
            origin='AWS/CloudWatch',
            event_type='cloudwatchAlarm',
            create_time=datetime.datetime.strptime(notification['Timestamp'], '%Y-%m-%dT%H:%M:%S.%fZ'),
            raw_data=notification,
        )

    elif notification['Type'] == 'Notification':

        alarm = json.loads(notification['Message'])

        return Alert(
            resource='%s:%s' % (alarm['Trigger']['Dimensions'][0]['name'], alarm['Trigger']['Dimensions'][0]['value']),
            event=alarm['Trigger']['MetricName'],
            environment='Production',
            severity=cw_state_to_severity(alarm['NewStateValue']),
            service=[alarm['AWSAccountId']],
            group='CloudWatch',
            value=alarm['NewStateReason'],
            text=alarm['AlarmDescription'],
            attributes=alarm['Trigger'],
            origin=alarm['Trigger']['Namespace'],
            event_type='cloudwatchAlarm',
            create_time=datetime.datetime.strptime(notification['Timestamp'], '%Y-%m-%dT%H:%M:%S.%fZ'),
            raw_data=alarm
        )


def cw_state_to_severity(state):

    if state == 'ALARM':
        return 'major'
    elif state == 'INSUFFICIENT_DATA':
        return 'warning'
    elif state == 'OK':
        return 'normal'
    else:
        return 'unknown'


def parse_pingdom(check):

    check = json.loads(check)

    if check['action'] == 'assign':
        return Alert(
            resource=check['host'],
            event=check['description'],
            correlate=['up', 'down'],
            environment='Production',
            severity='critical',
            service=['Unknown'],
            group='Network',
            text='%s is %s.' % (check['checkname'], check['description']),
            attributes={'incidentId': '#%s' % check['incidentid']},
            origin='Pingdom',
            event_type='availabilityAlert',
            raw_data=check,
        )
    elif check['action'] == 'notify_of_close':
        return Alert(
            resource=check['host'],
            event=check['description'],
            correlate=['up', 'down'],
            environment='Production',
            severity='normal',
            service=['Unknown'],
            group='Network',
            text='%s is %s.' % (check['checkname'], check['description']),
            attributes={'incidentId': '#%s' % check['incidentid']},
            origin='Pingdom',
            event_type='availabilityAlert',
            raw_data=check,
        )
    else:
        return Alert(
            resource=check['host'],
            event=check['description'],
            correlate=['up', 'down', check['description']],
            environment='Production',
            severity='indeterminate',
            service=['Unknown'],
            group='Network',
            text='%s is %s.' % (check['checkname'], check['description']),
            attributes={'incidentId': '#%s' % check['incidentid']},
            origin='Pingdom',
            event_type='availabilityAlert',
            raw_data=check,
        )



@app.route('/webhooks/cloudwatch', methods=['OPTIONS', 'POST'])
@cross_origin()
@jsonp
def cloudwatch():

    hook_started = webhook_timer.start_timer()
    try:
        incomingAlert = parse_notification(request.data)
    except ValueError, e:
        webhook_timer.stop_timer(hook_started)
        return jsonify(status="error", message=str(e)), 400

    try:
        alert = process_alert(incomingAlert)
    except RejectException as e:
        webhook_timer.stop_timer(hook_started)
        return jsonify(status="error", message=str(e)), 403
    except Exception as e:
        webhook_timer.stop_timer(hook_started)
        return jsonify(status="error", message=str(e)), 500

    webhook_timer.stop_timer(hook_started)

    if alert:
        body = alert.get_body()
        body['href'] = "%s/%s" % (request.base_url, alert.id)
        return jsonify(status="ok", id=alert.id, alert=body), 201, {'Location': '%s/%s' % (request.base_url, alert.id)}
    else:
        return jsonify(status="error", message="insert or update of cloudwatch alarm failed"), 500



@app.route('/webhooks/pingdom', methods=['OPTIONS', 'GET'])
@cross_origin()
@jsonp
def pingdom():

    hook_started = webhook_timer.start_timer()
    try:
        incomingAlert = parse_pingdom(request.args.get('message'))
    except ValueError, e:
        webhook_timer.stop_timer(hook_started)
        return jsonify(status="error", message=str(e)), 400

    try:
        alert = process_alert(incomingAlert)
    except RejectException as e:
        webhook_timer.stop_timer(hook_started)
        return jsonify(status="error", message=str(e)), 403
    except Exception as e:
        webhook_timer.stop_timer(hook_started)
        return jsonify(status="error", message=str(e)), 500

    webhook_timer.stop_timer(hook_started)

    if alert:
        body = alert.get_body()
        body['href'] = "%s/%s" % (request.base_url, alert.id)
        return jsonify(status="ok", id=alert.id, alert=body), 201, {'Location': '%s/%s' % (request.base_url, alert.id)}
    else:
        return jsonify(status="error", message="insert or update of pingdom check failed"), 500

