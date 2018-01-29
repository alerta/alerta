
from flask import request, g, jsonify
from flask_cors import cross_origin

from alerta.auth.utils import permission
from alerta.exceptions import ApiError
from alerta.models.alert import Alert
from . import webhooks


def parse_pagerduty(message):

    try:
        incident_key = message['data']['incident']['incident_key']
        incident_number = message['data']['incident']['incident_number']
        html_url = message['data']['incident']['html_url']
        incident_url = '<a href="%s">#%s</a>' % (html_url, incident_number)

        from alerta.models import status_code

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


@webhooks.route('/webhooks/pagerduty', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission('write:webhooks')
def pagerduty():

    data = request.json

    updated = False
    if data and 'messages' in data:
        for message in data['messages']:
            try:
                incident_key, status, text = parse_pagerduty(message)
            except ValueError as e:
                raise ApiError(str(e), 400)

            if not incident_key:
                raise ApiError('no incident key in PagerDuty data payload', 400)

            customer = g.get('customer', None)
            try:
                alert = Alert.find_by_id(id=incident_key, customer=customer)
            except Exception as e:
                raise ApiError(str(e), 500)

            if not alert:
                raise ApiError("not found", 404)

            try:
                updated = alert.set_status(status, text)
            except Exception as e:
                raise ApiError(str(e), 500)
    else:
        raise ApiError("no messages in PagerDuty data payload", 400)

    if updated:
        return jsonify(status="ok"), 200
    else:
        raise ApiError("update PagerDuty incident status failed", 500)
