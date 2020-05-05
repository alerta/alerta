import json
from typing import Any, Dict

from flask import current_app

from alerta.models.alert import Alert

from . import WebhookBase

JSON = Dict[str, Any]


class StackDriverWebhook(WebhookBase):
    """
    StackDriver Notification webhook
    See https://cloud.google.com/monitoring/support/notification-options#webhooks
    """

    def incoming(self, path, query_string, payload):

        incident = payload['incident']
        state = incident['state']

        # 'documentation' is an optional field that you can use to customize
        # your alert sending a json
        if 'documentation' in incident:
            try:
                content = json.loads(incident['documentation']['content'])
                incident.update(content)
            except Exception:
                current_app.logger.warning("Invalid documentation content: '{}'".format(incident['documentation']))

        status = None
        severity = incident.get('severity', 'critical')

        if state == 'open':
            status = None
        elif state == 'acknowledged':
            status = 'ack'
        elif state == 'closed':
            severity = 'ok'
        else:
            severity = 'indeterminate'

        service = []
        if incident['policy_name']:
            service.append(incident['policy_name'])

        return Alert(
            resource=incident['resource_name'],
            event=incident['condition_name'],
            environment=incident.get('environment', 'Production'),
            severity=severity,
            status=status,
            service=service,
            group=incident.get('group', 'Cloud'),
            text=incident['summary'],
            attributes={
                'incidentId': incident['incident_id'],
                'resourceId': incident['resource_id'],
                'moreInfo': '<a href="%s" target="_blank">Stackdriver Console</a>' % incident['url'],
                'startedAt': incident['started_at'],
                'endedAt': incident['ended_at']

            },
            customer=incident.get('customer'),
            origin=incident.get('origin', 'Stackdriver'),
            event_type='stackdriverAlert',
            raw_data=payload
        )
