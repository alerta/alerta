from typing import Any, Dict, Tuple

from flask import g, jsonify

from alerta.exceptions import ApiError
from alerta.models.alert import Alert

from . import WebhookBase

JSON = Dict[str, Any]


def parse_pagerduty(message: JSON) -> Tuple[str, str, str]:

    try:
        incident_key = message['data']['incident']['incident_key']
        incident_number = message['data']['incident']['incident_number']
        html_url = message['data']['incident']['html_url']
        incident_url = f'<a href="{html_url}">#{incident_number}</a>'

        if message['type'] == 'incident.trigger':
            status = 'open'
            user = message['data']['incident']['assigned_to_user']['name']
            text = f'Incident {incident_url} assigned to {user}'
        elif message['type'] == 'incident.acknowledge':
            status = 'ack'
            user = message['data']['incident']['assigned_to_user']['name']
            text = f'Incident {incident_url} acknowledged by {user}'
        elif message['type'] == 'incident.unacknowledge':
            status = 'open'
            text = f'Incident {incident_url} unacknowledged due to timeout'
        elif message['type'] == 'incident.resolve':
            status = 'closed'
            if message['data']['incident']['resolved_by_user']:
                user = message['data']['incident']['resolved_by_user']['name']
            else:
                user = 'n/a'
            text = f'Incident {incident_url} resolved by {user}'
        elif message['type'] == 'incident.assign':
            status = 'assign'
            user = message['data']['incident']['assigned_to_user']['name']
            text = f'Incident {incident_url} manually assigned to {user}'
        elif message['type'] == 'incident.escalate':
            status = 'open'
            user = message['data']['incident']['assigned_to_user']['name']
            text = f'Incident {incident_url} escalated to {user}'
        elif message['type'] == 'incident.delegate':
            status = 'open'
            user = message['data']['incident']['assigned_to_user']['name']
            text = f'Incident {incident_url} reassigned due to escalation to {user}'
        else:
            status = 'unknown'
            text = message['type']
    except Exception as e:
        raise ValueError(e)

    return incident_key, status, text


class PagerDutyWebhook(WebhookBase):
    """
    PagerDuty incident webhook
    See https://v2.developer.pagerduty.com/docs/webhooks-v2-overview
    """

    def incoming(self, path, query_string, payload):

        updated = False
        if payload and 'messages' in payload:
            for message in payload['messages']:
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

            if updated:
                return jsonify(status='ok')
            else:
                raise ApiError('update PagerDuty incident status failed', 500)

        else:
            raise ApiError('no messages in PagerDuty data payload', 400)
