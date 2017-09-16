
import datetime
import pytz

try:
    import simplejson as json
except ImportError:
    import json

from copy import copy
from dateutil.parser import parse as parse_date
from flask import g, request, jsonify
from flask_cors import cross_origin

from alerta.app import app, db
from alerta.app.auth import permission
from alerta.app.metrics import Timer
from alerta.app.utils import absolute_url, process_alert, add_remote_ip
from alerta.app.alert import Alert
from alerta.app.exceptions import RejectException

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
            create_time=datetime.datetime.strptime(notification['Timestamp'], '%Y-%m-%dT%H:%M:%S.%fZ'),
            raw_data=alarm
        )


@app.route('/webhooks/cloudwatch', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission('write:webhooks')
def cloudwatch():

    hook_started = webhook_timer.start_timer()
    try:
        incomingAlert = parse_notification(request.data)
    except ValueError as e:
        webhook_timer.stop_timer(hook_started)
        return jsonify(status="error", message=str(e)), 400

    if g.get('customer', None):
        incomingAlert.customer = g.get('customer')

    add_remote_ip(request, incomingAlert)

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


# {
#     "second_probe": {},
#     "check_type": "HTTP",
#     "first_probe": {},
#     "tags": [],
#     "check_id": 803318,
#     "current_state": "DOWN",
#     "check_params": {
#         "url": "/",
#         "encryption": false,
#         "hostname": "api.alerta.io",
#         "basic_auth": false,
#         "port": 80,
#         "header": "User-Agent:Pingdom.com_bot_version_1.4_(http://www.pingdom.com/)",
#         "ipv6": false,
#         "full_url": "http://api.alerta.io/"
#     },
#     "previous_state": "UP",
#     "check_name": "Alerta API on OpenShift",
#     "version": 1,
#     "state_changed_timestamp": 1498859836,
#     "importance_level": "HIGH",
#     "state_changed_utc_time": "2017-06-30T21:57:16",
#     "long_description": "This is a test message triggered by a user in My Pingdom",
#     "description": "test"
# }



def parse_pingdom(check):

    if check['importance_level'] == 'HIGH':
        severity = 'critical'
    else:
        severity = 'warning'

    if check['current_state'] == 'UP':
        severity = 'normal'

    return Alert(
        resource=check['check_name'],
        event=check['current_state'],
        correlate=['UP', 'DOWN'],
        environment='Production',
        severity=severity,
        service=[check['check_type']],
        group='Network',
        value=check['description'],
        text='%s: %s' % (check['importance_level'], check['long_description']),
        tags=check['tags'],
        attributes={'checkId': check['check_id']},
        origin='Pingdom',
        event_type='availabilityAlert',
        raw_data=check
    )


@app.route('/webhooks/pingdom', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission('write:webhooks')
def pingdom():

    LOG.info(json.dumps(request.json))

    hook_started = webhook_timer.start_timer()
    try:
        incomingAlert = parse_pingdom(request.json)
    except ValueError as e:
        webhook_timer.stop_timer(hook_started)
        return jsonify(status="error", message=str(e)), 400

    if g.get('customer', None):
        incomingAlert.customer = g.get('customer')

    add_remote_ip(request, incomingAlert)

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

    try:
        incident_key = message['data']['incident']['incident_key']
        incident_number = message['data']['incident']['incident_number']
        html_url = message['data']['incident']['html_url']
        incident_url = '<a href="%s">#%s</a>' % (html_url, incident_number)

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
    except Exception:
        raise ValueError

    return incident_key, status, text


@app.route('/webhooks/pagerduty', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission('write:webhooks')
def pagerduty():

    hook_started = webhook_timer.start_timer()
    data = request.json

    updated = False
    if data and 'messages' in data:
        for message in data['messages']:
            try:
                incident_key, status, text = parse_pagerduty(message)
            except ValueError as e:
                webhook_timer.stop_timer(hook_started)
                return jsonify(status="error", message=str(e)), 400

            customer = g.get('customer', None)
            try:
                alert = db.get_alert(id=incident_key, customer=customer)
            except Exception as e:
                webhook_timer.stop_timer(hook_started)
                return jsonify(status="error", message=str(e)), 500

            if not alert:
                webhook_timer.stop_timer(hook_started)
                return jsonify(stats="error", message="not found"), 404

            try:
                updated = db.set_status(id=alert.id, status=status, text=text)
            except Exception as e:
                webhook_timer.stop_timer(hook_started)
                return jsonify(status="error", message=str(e)), 500
    else:
        webhook_timer.stop_timer(hook_started)
        return jsonify(status="error", message="no messages in PagerDuty data payload"), 400

    webhook_timer.stop_timer(hook_started)
    if updated:
        return jsonify(status="ok"), 200
    else:
        return jsonify(status="error", message="update PagerDuty incident status failed"), 500


def parse_prometheus(alert, external_url):

    status = alert.get('status', 'firing')

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

    try:
        timeout = int(labels.pop('timeout', 0)) or None
    except ValueError:
        timeout = None

    if external_url:
        annotations['externalUrl'] = external_url
    if 'generatorURL' in alert:
        annotations['moreInfo'] = '<a href="%s" target="_blank">Prometheus Graph</a>' % alert['generatorURL']

    return Alert(
        resource=labels.pop('exported_instance', None) or labels.pop('instance', 'n/a'),
        event=labels.pop('alertname'),
        environment=labels.pop('environment', 'Production'),
        severity=severity,
        correlate=labels.pop('correlate').split(',') if 'correlate' in labels else None,
        service=labels.pop('service', '').split(','),
        group=labels.pop('job', 'Prometheus'),
        value=labels.pop('value', None),
        text=text,
        attributes=annotations,
        origin='prometheus/' + labels.pop('monitor', '-'),
        event_type='prometheusAlert',
        create_time=create_time.astimezone(tz=pytz.UTC).replace(tzinfo=None),
        timeout=timeout,
        raw_data=alert,
        tags=["%s=%s" % t for t in labels.items()]  # any labels left are used for tags
    )


@app.route('/webhooks/prometheus', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission('write:webhooks')
def prometheus():

    alerts = []
    if request.json and 'alerts' in request.json:
        hook_started = webhook_timer.start_timer()
        external_url = request.json.get('externalURL', None)
        for alert in request.json['alerts']:
            try:
                incomingAlert = parse_prometheus(alert, external_url)
            except ValueError as e:
                webhook_timer.stop_timer(hook_started)
                return jsonify(status="error", message=str(e)), 400

            if g.get('customer', None):
                incomingAlert.customer = g.get('customer')

            add_remote_ip(request, incomingAlert)

            try:
                alert = process_alert(incomingAlert)
            except RejectException as e:
                webhook_timer.stop_timer(hook_started)
                return jsonify(status="error", message=str(e)), 403
            except Exception as e:
                webhook_timer.stop_timer(hook_started)
                return jsonify(status="error", message=str(e)), 500
            alerts.append(alert)

        webhook_timer.stop_timer(hook_started)
    else:
        return jsonify(status="error", message="no alerts in Prometheus notification payload"), 400

    if len(alerts) == 1:
        body = alerts[0].get_body()
        body['href'] = absolute_url('/alert/' + alerts[0].id)
        return jsonify(status="ok", id=alerts[0].id, alert=body), 201, {'Location': body['href']}
    else:
        return jsonify(status="ok", ids=[alert.id for alert in alerts]), 201


def parse_stackdriver(notification):

    incident = notification['incident']
    state = incident['state']

    if state == 'open':
        severity = 'critical'
        status = None
        create_time = datetime.datetime.fromtimestamp(incident['started_at'])
    elif state == 'acknowledged':
        severity = 'critical'
        status = 'ack'
        create_time = None
    elif state == 'closed':
        severity = 'ok'
        status = None
        create_time = datetime.datetime.fromtimestamp(incident['ended_at'])
    else:
        severity = 'indeterminate'
        status = None
        create_time = None

    return Alert(
        resource=incident['resource_name'],
        event=incident['condition_name'],
        environment='Production',
        severity=severity,
        status=status,
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
@permission('write:webhooks')
def stackdriver():

    hook_started = webhook_timer.start_timer()
    try:
        incomingAlert = parse_stackdriver(request.get_json(force=True))
    except ValueError as e:
        webhook_timer.stop_timer(hook_started)
        return jsonify(status="error", message=str(e)), 400

    if g.get('customer', None):
        incomingAlert.customer = g.get('customer')

    add_remote_ip(request, incomingAlert)

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


def parse_serverdensity(alert):

    if alert['fixed']:
        severity = 'ok'
    else:
        severity = 'critical'

    return Alert(
        resource=alert['item_name'],
        event=alert['alert_type'],
        environment='Production',
        severity=severity,
        service=[alert['item_type']],
        group=alert['alert_section'],
        value=alert['configured_trigger_value'],
        text='Alert created for %s:%s' % (alert['item_type'], alert['item_name']),
        tags=['cloud'] if alert['item_cloud'] else [],
        attributes={
            'alertId': alert['alert_id'],
            'itemId': alert['item_id']
        },
        origin='ServerDensity',
        event_type='serverDensityAlert',
        raw_data=alert
    )


@app.route('/webhooks/serverdensity', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission('write:webhooks')
def serverdensity():

    hook_started = webhook_timer.start_timer()
    try:
        incomingAlert = parse_serverdensity(request.json)
    except ValueError as e:
        webhook_timer.stop_timer(hook_started)
        return jsonify(status="error", message=str(e)), 400

    if g.get('customer', None):
        incomingAlert.customer = g.get('customer')

    add_remote_ip(request, incomingAlert)

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
        return jsonify(status="error", message="insert or update of serverdensity alert failed"), 500


def parse_newrelic(alert):

    if 'version' not in alert:
        raise ValueError("New Relic Legacy Alerting is not supported")

    status = alert['current_state'].lower()
    if status == 'open':
        severity = alert['severity'].lower()
    elif status == 'acknowledged':
        severity = alert['severity'].lower()
        status = 'ack'
    elif status == 'closed':
        severity = 'ok'
    else:
        severity = alert['severity'].lower()

    return Alert(
        resource=alert['targets'][0]['name'],
        event=alert['condition_name'],
        environment='Production',
        severity=severity,
        status=status,
        service=[alert['account_name']],
        group=alert['targets'][0]['type'],
        text=alert['details'],
        tags=['%s:%s' % (key, value) for (key, value) in alert['targets'][0]['labels'].items()],
        attributes={
            'moreInfo': '<a href="%s" target="_blank">Incident URL</a>' % alert['incident_url'],
            'runBook': '<a href="%s" target="_blank">Runbook URL</a>' % alert['runbook_url']
        },
        origin='New Relic/v%s' % alert['version'],
        event_type=alert['event_type'].lower(),
        raw_data=alert
    )


@app.route('/webhooks/newrelic', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission('write:webhooks')
def newrelic():

    hook_started = webhook_timer.start_timer()
    try:
        incomingAlert = parse_newrelic(request.json)
    except ValueError as e:
        webhook_timer.stop_timer(hook_started)
        return jsonify(status="error", message=str(e)), 400

    if g.get('customer', None):
        incomingAlert.customer = g.get('customer')

    add_remote_ip(request, incomingAlert)

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
        return jsonify(status="error", message="insert or update of New Relic alert failed"), 500


def parse_grafana(alert, match):

    if alert['state'] == 'alerting':
        severity = 'major'
    elif alert['state'] == 'ok':
        severity = 'normal'
    else:
        severity = 'indeterminate'

    attributes = {
        'ruleId': alert['ruleId']
    }
    if 'ruleUrl' in alert:
        attributes['ruleUrl'] = '<a href="%s" target="_blank">Rule</a>' % alert['ruleUrl']
    if 'imageUrl' in alert:
        attributes['imageUrl'] = '<a href="%s" target="_blank">Image</a>' % alert['imageUrl']

    return Alert(
        resource=match['metric'],
        event=alert['ruleName'],
        environment='Production',
        severity=severity,
        service=['Grafana'],
        group='Performance',
        value='%s' % match['value'],
        text=alert.get('message', None) or alert.get('title', alert['state']),
        tags=match.get('tags', []),
        attributes=attributes,
        origin='Grafana',
        event_type='performanceAlert',
        timeout=300,
        raw_data=alert
    )


@app.route('/webhooks/grafana', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission('write:webhooks')
def grafana():

    hook_started = webhook_timer.start_timer()

    alerts = []
    data = request.json
    if data and data['state'] == 'alerting':
        for match in data.get('evalMatches', []):
            try:
                incomingAlert = parse_grafana(data, match)
            except ValueError as e:
                webhook_timer.stop_timer(hook_started)
                return jsonify(status="error", message=str(e)), 400

            if g.get('customer', None):
                incomingAlert.customer = g.get('customer')

            add_remote_ip(request, incomingAlert)

            try:
                alert = process_alert(incomingAlert)
            except RejectException as e:
                webhook_timer.stop_timer(hook_started)
                return jsonify(status="error", message=str(e)), 403
            except Exception as e:
                webhook_timer.stop_timer(hook_started)
                return jsonify(status="error", message=str(e)), 500
            alerts.append(alert)

        webhook_timer.stop_timer(hook_started)

    elif data and data['state'] == 'ok' and data.get('ruleId', None):
        try:
            existingAlerts = db.get_alerts({'attributes.ruleId': data['ruleId'], 'customer': g.get('customer', None)})
        except Exception as e:
            webhook_timer.stop_timer(hook_started)
            return jsonify(status="error", message=str(e)), 500

        for updateAlert in existingAlerts:
            updateAlert.severity = 'normal'
            updateAlert.status = 'closed'

            try:
                alert = process_alert(updateAlert)
            except RejectException as e:
                webhook_timer.stop_timer(hook_started)
                return jsonify(status="error", message=str(e)), 403
            except Exception as e:
                webhook_timer.stop_timer(hook_started)
                return jsonify(status="error", message=str(e)), 500
            alerts.append(alert)

        webhook_timer.stop_timer(hook_started)
    else:
        return jsonify(status="error", message="no alerts in Grafana notification payload"), 400

    if len(alerts) == 1:
        body = alerts[0].get_body()
        body['href'] = absolute_url('/alert/' + alerts[0].id)
        return jsonify(status="ok", id=alerts[0].id, alert=body), 201, {'Location': body['href']}
    else:
        return jsonify(status="ok", ids=[alert.id for alert in alerts]), 201


def send_message_replay(alert_id, action, user, data):
    try:
        import telepot
    except ImportError as e:
        LOG.warning("You have configured Telegram but 'telepot' client is not installed", exec_info=True)
        return

    try:
        bot = telepot.Bot(app.config.get('TELEGRAM_TOKEN'))
        dashboard_url = app.config.get('DASHBOARD_URL')

        # message info
        message_id = data['callback_query']['message']['message_id']
        message_log = "\n".join(data['callback_query']['message']['text'].split('\n')[1:])

        # process buttons for reply text
        alert = db.get_alert(alert_id)
        inline_keyboard, reply = [], "The status of alert {alert} is *{status}* now!"

        actions = ['watch', 'unwatch']
        if action in actions:
            reply = "User `{user}` is _{status}ing_ alert {alert}"
            next_action = actions[(actions.index(action) + 1) % len(actions)]
            inline_keyboard = [
                [{'text': next_action.capitalize(), 'callback_data': "/{} {}".format(next_action, alert_id)},
                 {'text': 'Ack', 'callback_data': "{} {}".format('/ack', alert_id)},
                 {'text': 'Close', 'callback_data': "{} {}".format('/close', alert_id)}, ]
            ]

        # format message response
        alert_short_id = alert.get_id(short=True)
        alert_url = "{}/#/alert/{}".format(dashboard_url, alert.id)
        reply = reply.format(alert=alert_short_id, status=action, user=user)
        message = "{alert} *{level} - {event} on {resouce}*\n{log}\n{reply}".format(
            alert="[{}]({})".format(alert_short_id, alert_url), level=alert.severity.capitalize(),
            event=alert.event, resouce=alert.resource, log=message_log, reply=reply)

        # send message
        bot.editMessageText(
            msg_identifier=(app.config.get('TELEGRAM_CHAT_ID'), message_id), text=message,
            parse_mode='Markdown', reply_markup={'inline_keyboard': inline_keyboard}
        )
    except Exception as e:
        LOG.warning("Error sending reply message", exec_info=True)


@app.route('/webhooks/telegram', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission('write:webhooks')
def telegram():
    data = request.json
    if 'callback_query' in data:
        author = data['callback_query']['from']
        command, alert = data['callback_query']['data'].split(' ', 1)
        user = "{} {}".format(author.get('first_name'), author.get('last_name'))

        action = command.lstrip('/')
        if action in ['open', 'ack', 'close']:
            db.set_status(alert, action, 'status change via Telegram')
        elif action in ['watch', 'unwatch']:
            db.untag_alert(alert, ["{}:{}".format(action, user), ])
        elif action == 'blackout':
            environment, resource, event = alert.split('|', 2)
            db.create_blackout(environment, resource=resource, event=event)

        send_message_replay(alert, action, user, data)
        return jsonify(status="ok")
    else:
        return jsonify(status="error", message="no callback_query in Telegram message"), 400


def parse_riemann(alert):

    return Alert(
        resource='%s-%s' % (alert['host'], alert['service']),
        event=alert.get('event', alert['service']),
        environment=alert.get('environment', 'Production'),
        severity=alert.get('state', 'unknown'),
        service=[alert['service']],
        group=alert.get('group', 'Performance'),
        text=alert.get('description', None),
        value=alert.get('metric', None),
        tags=alert.get('tags', None),
        origin='Riemann',
        raw_data=alert
    )


@app.route('/webhooks/riemann', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission('write:webhooks')
def riemann():

    hook_started = webhook_timer.start_timer()
    try:
        incomingAlert = parse_riemann(request.json)
    except ValueError as e:
        webhook_timer.stop_timer(hook_started)
        return jsonify(status="error", message=str(e)), 400

    if g.get('customer', None):
        incomingAlert.customer = g.get('customer')

    add_remote_ip(request, incomingAlert)

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
        return jsonify(status="error", message="insert or update of Riemann alert failed"), 500


def parse_slack(data):
    payload = json.loads(data['payload'])

    user = payload.get('user', {}).get('name')
    alert_key = payload.get('callback_id')
    action = payload.get('actions', [{}])[0].get('value')

    try:
        alert = db.get_alert(id=alert_key)
    except Exception as e:
        LOG.error(u'User {} is doing a non existent action {}'.format(user, action))

    if not alert:
        raise ValueError(u'Alert {} not match'.format(alert_key))
    elif not user:
        raise ValueError(u'User {} not exist'.format(user))
    elif not action:
        raise ValueError(u'Non existent action {}'.format(action))

    return alert, user, action


def build_slack_response(alert, action, user, data):
    response = json.loads(data['payload']).get('original_message', {})

    actions = ['watch', 'unwatch']
    message = (
        u"User {user} is {action}ing alert {alert}" if action in actions else
        u"The status of alert {alert} is {status} now!").format(
        alert=alert.get_id(short=True), status=alert.status.capitalize(),
        action=action, user=user
    )

    attachment_response = {
        "fallback": message, "pretext": "Action done!", "color": "#808080",
        "title": message, "title_link": absolute_url('/alert/' + alert.id)
    }

    # clear interactive buttons and add new attachment as response of action
    if action not in actions:
        attachments = response.get('attachments', [])
        for attachment in attachments:
            attachment.pop('actions', None)
        attachments.append(attachment_response)
        response['attachments'] = attachments
        return response

    # update the interactive button of all actions
    next_action = actions[(actions.index(action) + 1) % len(actions)]
    for attachment in response.get('attachments', []):
        for attached_action in attachment.get('actions', []):
            if action == attached_action.get('value'):
                attached_action.update({
                    'name': next_action, 'value': next_action,
                    'text': next_action.capitalize()
                })

    return response


@app.route('/webhooks/slack', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission('write:webhooks')
def slack():
    hook_started = webhook_timer.start_timer()
    try:
        alert, user, action = parse_slack(request.form)
    except ValueError as e:
        webhook_timer.stop_timer(hook_started)
        return jsonify(stats="error", message="not found"), 404
    except Exception as e:
        webhook_timer.stop_timer(hook_started)
        return jsonify(status="error", message=str(e)), 500

    if action in ['open', 'ack', 'close']:
        try:
            alert = db.set_status(alert.id, action, u"status change via Slack by {}".format(user))
        except RejectException as e:
            webhook_timer.stop_timer(hook_started)
            return jsonify(status="error", message=str(e)), 403
        except Exception as e:
            webhook_timer.stop_timer(hook_started)
            return jsonify(status="error", message=str(e)), 500

    elif action in ['watch', 'unwatch']:
        db.untag_alert(alert.id, ["{}:{}".format(action, user), ])

    else:
        webhook_timer.stop_timer(hook_started)
        return jsonify(status="error", message=u'Unsuported action'), 403

    response = build_slack_response(alert, action, user, request.form)

    webhook_timer.stop_timer(hook_started)
    return jsonify(**response), 201
