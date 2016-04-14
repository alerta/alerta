import json
import datetime

from copy import copy
from dateutil.parser import parse as parse_date
from flask import g, request
from flask.ext.cors import cross_origin

from alerta.app import app, db
from alerta.app.auth import auth_required
from alerta.app.metrics import Timer
from alerta.app.utils import absolute_url, jsonify, process_alert
from alerta.alert import Alert
from alerta.plugins import RejectException

LOG = app.logger

webhook_timer = Timer('alerts', 'webhook', 'Web hook alerts', 'Total time to process number of web hook alerts')
duplicate_timer = Timer('alerts', 'duplicate', 'Duplicate alerts', 'Total time to process number of duplicate alerts')
correlate_timer = Timer('alerts', 'correlate', 'Correlated alerts', 'Total time to process number of correlated alerts')
create_timer = Timer('alerts', 'create', 'Newly created alerts', 'Total time to process number of new alerts')


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
            create_time=datetime.datetime.strptime(notification['Timestamp'], '%Y-%m-%dT%H:%M:%S.%fZ'),
            raw_data=notification,
        )

    elif notification['Type'] == 'Notification':

        alarm = json.loads(notification['Message'])

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
            create_time=datetime.datetime.strptime(notification['Timestamp'], '%Y-%m-%dT%H:%M:%S.%fZ'),
            raw_data=alarm
        )


@app.route('/webhooks/cloudwatch', methods=['OPTIONS', 'POST'])
@cross_origin()
@auth_required
def cloudwatch():

    hook_started = webhook_timer.start_timer()
    try:
        incomingAlert = parse_notification(request.data)
    except ValueError as e:
        webhook_timer.stop_timer(hook_started)
        return jsonify(status="error", message=str(e)), 400

    if g.get('customer', None):
        incomingAlert.customer = g.get('customer')

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
        body['href'] = absolute_url('/alert/' + alert.id)
        return jsonify(status="ok", id=alert.id, alert=body), 201, {'Location': body['href']}
    else:
        return jsonify(status="error", message="insert or update of cloudwatch alarm failed"), 500


def parse_pingdom(check):

    check = json.loads(check)

    if check['action'] == 'assign':
        return Alert(
            resource=check['host'],
            event=check['description'],
            correlate=['up', 'down'],
            environment='Production',
            severity='critical',
            service=[check['checkname']],
            group='Network',
            text='%s is %s.' % (check['checkname'], check['description']),
            attributes={'incidentKey': check['incidentid']},
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
            service=[check['checkname']],
            group='Network',
            text='%s is %s.' % (check['checkname'], check['description']),
            attributes={'incidentKey': check['incidentid']},
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
            service=[check['checkname']],
            group='Network',
            text='%s is %s.' % (check['checkname'], check['description']),
            attributes={'incidentKey': check['incidentid']},
            origin='Pingdom',
            event_type='availabilityAlert',
            raw_data=check,
        )

@app.route('/webhooks/pingdom', methods=['OPTIONS', 'GET'])
@cross_origin()
@auth_required
def pingdom():

    hook_started = webhook_timer.start_timer()
    try:
        incomingAlert = parse_pingdom(request.args.get('message'))
    except ValueError as e:
        webhook_timer.stop_timer(hook_started)
        return jsonify(status="error", message=str(e)), 400

    if g.get('customer', None):
        incomingAlert.customer = g.get('customer')

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
        body['href'] = absolute_url('/alert/' + alert.id)
        return jsonify(status="ok", id=alert.id, alert=body), 201, {'Location': body['href']}
    else:
        return jsonify(status="error", message="insert or update of pingdom check failed"), 500


def parse_pagerduty(message):

    incident_key = message['data']['incident']['incident_key']
    incident_number = message['data']['incident']['incident_number']
    html_url = message['data']['incident']['html_url']
    incident_url = '<a href="%s">#%s</a>' % (html_url, incident_number)

    try:
        alert = db.get_alerts(query={'attributes.incidentKey': incident_key}, limit=1)[0]
    except IndexError:
        raise

    from alerta.app import status_code

    if message['type'] == 'incident.trigger':
        status = status_code.OPEN
        user = message['data']['incident']['assigned_to_user']['name']
        text = 'Incident %s assigned to %s' % (incident_url, user)
    elif message['type'] == 'incident.acknowledge':
        status = status_code.ACK
        user = message['data']['incident']['assigned_to_user']['name']
        text = 'Incident %s acknowledged by %s' % (incident_url, user)
    elif message['type'] == 'incident.unacknowledge':
        status = status_code.OPEN
        text = 'Incident %s unacknowledged due to timeout' % incident_url
    elif message['type'] == 'incident.resolve':
        status = status_code.CLOSED
        if message['data']['incident']['resolved_by_user']:
            user = message['data']['incident']['resolved_by_user']['name']
        else:
            user = 'n/a'
        text = 'Incident %s resolved by %s' % (incident_url, user)
    elif message['type'] == 'incident.assign':
        status = status_code.ASSIGN
        user = message['data']['incident']['assigned_to_user']['name']
        text = 'Incident %s manually assigned to %s' % (incident_url, user)
    elif message['type'] == 'incident.escalate':
        status = status_code.OPEN
        user = message['data']['incident']['assigned_to_user']['name']
        text = 'Incident %s escalated to %s' % (incident_url, user)
    elif message['type'] == 'incident.delegate':
        status = status_code.OPEN
        user = message['data']['incident']['assigned_to_user']['name']
        text = 'Incident %s reassigned due to escalation to %s' % (incident_url, user)
    else:
        status = status_code.UNKNOWN
        text = message['type']

    return alert.id, status, text


@app.route('/webhooks/pagerduty', methods=['OPTIONS', 'POST'])
@cross_origin()
@auth_required
def pagerduty():

    hook_started = webhook_timer.start_timer()
    data = request.json

    if data and 'messages' in data:
        for message in data['messages']:
            try:
                id, status, text = parse_pagerduty(message)
            except IndexError as e:
                webhook_timer.stop_timer(hook_started)
                return jsonify(status="error", message=str(e)), 400

            try:
                alert = db.set_status(id=id, status=status, text=text)
            except Exception as e:
                webhook_timer.stop_timer(hook_started)
                return jsonify(status="error", message=str(e)), 500
    else:
        webhook_timer.stop_timer(hook_started)
        return jsonify(status="error", message="no messages in PagerDuty data payload"), 400

    webhook_timer.stop_timer(hook_started)

    if alert:
        return jsonify(status="ok"), 200
    else:
        return jsonify(status="error", message="update PagerDuty incident status failed"), 500


def parse_prometheus(status, alert):

    labels = copy(alert['labels'])
    annotations = copy(alert['annotations'])

    starts_at = parse_date(alert['startsAt'])
    if alert['endsAt'] == '0001-01-01T00:00:00Z':
        ends_at = None
    else:
        ends_at = parse_date(alert['endsAt'])

    if status == 'firing':
        severity = labels.pop('severity', 'warning')
        create_time = starts_at
    elif status == 'resolved':
        severity = 'normal'
        create_time = ends_at
    else:
        severity = 'unknown'
        create_time = ends_at or starts_at

    summary = annotations.pop('summary', None)
    description = annotations.pop('description', None)
    text = description or summary or '%s: %s on %s' % (labels['job'], labels['alertname'], labels['instance'])

    if 'generatorURL' in alert:
        annotations['moreInfo'] = '<a href="%s" target="_blank">Prometheus Graph</a>' % alert['generatorURL']

    return Alert(
        resource=labels.pop('exported_instance', None) or labels.pop('instance'),
        event=labels.pop('alertname'),
        environment=labels.pop('environment', 'Production'),
        severity=severity,
        correlate=labels.pop('correlate').split(',') if 'correlate' in labels else None,
        service=labels.pop('service', '').split(','),
        group=labels.pop('group', None),
        value=labels.pop('value', None),
        text=text,
        customer=labels.pop('customer', None),
        tags=["%s=%s" % t for t in labels.items()],
        attributes=annotations,
        origin='prometheus/' + labels.get('job', '-'),
        event_type='prometheusAlert',
        create_time=create_time,
        raw_data=alert
    )


@app.route('/webhooks/prometheus', methods=['OPTIONS', 'POST'])
@cross_origin()
@auth_required
def prometheus():

    if request.json and 'alerts' in request.json:
        hook_started = webhook_timer.start_timer()
        status = request.json['status']
        for alert in request.json['alerts']:
            try:
                incomingAlert = parse_prometheus(status, alert)
            except ValueError as e:
                webhook_timer.stop_timer(hook_started)
                return jsonify(status="error", message=str(e)), 400

            if g.get('customer', None):
                incomingAlert.customer = g.get('customer')

            try:
                process_alert(incomingAlert)
            except RejectException as e:
                webhook_timer.stop_timer(hook_started)
                return jsonify(status="error", message=str(e)), 403
            except Exception as e:
                webhook_timer.stop_timer(hook_started)
                return jsonify(status="error", message=str(e)), 500

        webhook_timer.stop_timer(hook_started)
    else:
        return jsonify(status="error", message="no alerts in Prometheus notification payload"), 400

    return jsonify(status="ok"), 200


def parse_stackdriver(notification):

    notification = json.loads(notification)
    incident = notification['incident']
    state = incident['state']

    if state == 'acknowledged':
        try:
            alert = db.get_alerts(query={'attributes.incidentId': incident['incident_id']}, limit=1)[0]
        except IndexError:
            raise ValueError('unknown Stackdriver Incident ID: %s' % incident['incident_id'])
        return state, alert

    else:
        if state == 'open':
            severity = 'critical'
            create_time = datetime.datetime.fromtimestamp(incident['started_at'])
        elif state == 'closed':
            severity = 'ok'
            create_time = datetime.datetime.fromtimestamp(incident['ended_at'])
        else:
            severity = 'indeterminate'
            create_time = None

        return state, Alert(
            resource=incident['resource_name'],
            event=incident['condition_name'],
            environment='Production',
            severity=severity,
            service=[incident['policy_name']],
            group='Cloud',
            text=incident['summary'],
            attributes={
                'incidentId': incident['incident_id'],
                'resourceId': incident['resource_id'],
                'moreInfo': '<a href="%s" target="_blank">Stackdriver Console</a>' % incident['url']
            },
            origin='Stackdriver',
            event_type='stackdriverAlert',
            create_time=create_time,
            raw_data=notification
        )


@app.route('/webhooks/stackdriver', methods=['OPTIONS', 'POST'])
@cross_origin()
@auth_required
def stackdriver():

    hook_started = webhook_timer.start_timer()
    try:
        state, incomingAlert = parse_stackdriver(request.data)
    except ValueError as e:
        webhook_timer.stop_timer(hook_started)
        return jsonify(status="error", message=str(e)), 400

    if g.get('customer', None):
        incomingAlert.customer = g.get('customer')

    if state == 'acknowledged':
        try:
            alert = db.set_status(id=incomingAlert.id, status='ack', text='acknowledged via Stackdriver')
        except Exception as e:
            webhook_timer.stop_timer(hook_started)
            return jsonify(status="error", message=str(e)), 500
    else:
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
        body['href'] = absolute_url('/alert/' + alert.id)
        return jsonify(status="ok", id=alert.id, alert=body), 201, {'Location': body['href']}
    else:
        return jsonify(status="error", message="notification from stackdriver failed"), 500
