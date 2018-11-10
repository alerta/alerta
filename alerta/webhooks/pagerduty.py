from typing import Any, Dict, Tuple

from flask import current_app, g, jsonify, request
from flask_cors import cross_origin

from alerta.auth.decorators import permission
from alerta.exceptions import ApiError
from alerta.models.alert import Alert
from alerta.models.enums import Scope
from alerta.utils.audit import write_audit_trail

from . import webhooks

JSON = Dict[str, Any]


def parse_pagerduty(message: JSON) -> Tuple[str, str, str]:

    try:
        incident_key = message['data']['incident']['incident_key']
        incident_number = message['data']['incident']['incident_number']
        html_url = message['data']['incident']['html_url']
        incident_url = '<a href="{}">#{}</a>'.format(html_url, incident_number)

        if message['type'] == 'incident.trigger':
            status = 'open'
            user = message['data']['incident']['assigned_to_user']['name']
            text = 'Incident {} assigned to {}'.format(incident_url, user)
        elif message['type'] == 'incident.acknowledge':
            status = 'ack'
            user = message['data']['incident']['assigned_to_user']['name']
            text = 'Incident {} acknowledged by {}'.format(incident_url, user)
        elif message['type'] == 'incident.unacknowledge':
            status = 'open'
            text = 'Incident %s unacknowledged due to timeout' % incident_url
        elif message['type'] == 'incident.resolve':
            status = 'closed'
            if message['data']['incident']['resolved_by_user']:
                user = message['data']['incident']['resolved_by_user']['name']
            else:
                user = 'n/a'
            text = 'Incident {} resolved by {}'.format(incident_url, user)
        elif message['type'] == 'incident.assign':
            status = 'assign'
            user = message['data']['incident']['assigned_to_user']['name']
            text = 'Incident {} manually assigned to {}'.format(incident_url, user)
        elif message['type'] == 'incident.escalate':
            status = 'open'
            user = message['data']['incident']['assigned_to_user']['name']
            text = 'Incident {} escalated to {}'.format(incident_url, user)
        elif message['type'] == 'incident.delegate':
            status = 'open'
            user = message['data']['incident']['assigned_to_user']['name']
            text = 'Incident {} reassigned due to escalation to {}'.format(incident_url, user)
        else:
            status = 'unknown'
            text = message['type']
    except Exception as e:
        raise ValueError(e)

    return incident_key, status, text


@webhooks.route('/webhooks/pagerduty', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission(Scope.write_webhooks)
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

            customers = g.get('customers', None)
            try:
                alert = Alert.find_by_id(id=incident_key, customers=customers)
            except Exception as e:
                raise ApiError(str(e), 500)

            if not alert:
                raise ApiError('not found', 404)

            try:
                updated = alert.set_status(status, text)
            except Exception as e:
                raise ApiError(str(e), 500)

            text = 'alert updated via pagerduty webhook'
            write_audit_trail.send(current_app._get_current_object(), event='webhook-updated', message=text, user=g.user,
                                   customers=g.customers, scopes=g.scopes, resource_id=alert.id, type='alert',
                                   request=request)
    else:
        raise ApiError('no messages in PagerDuty data payload', 400)

    if updated:
        return jsonify(status='ok'), 200
    else:
        raise ApiError('update PagerDuty incident status failed', 500)
