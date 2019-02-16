import json
from datetime import datetime
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

    def incoming(self, query_string, payload):

        incident = payload['incident']
        state = incident['state']

        # 'documentation' is an optional field that you can use to customize
        # your alert sending a json
        if 'documentation' in incident:
            try:
                content = json.loads(incident['documentation']['content'])
                incident.update(content)
            except Exception as e:
                current_app.logger.warning("Invalid documentation content: '{}'".format(incident['documentation']))

        service = []
        status = None
        create_time = None  # type: ignore
        severity = incident.get('severity', 'critical')

        if incident['policy_name']:
            service.append(incident['policy_name'])

        if state == 'open':
            create_time = datetime.utcfromtimestamp(incident['started_at'])
        elif state == 'acknowledged':
            status = 'ack'
        elif state == 'closed':
            severity = 'ok'
            create_time = datetime.utcfromtimestamp(incident['ended_at'])
        else:
            severity = 'indeterminate'

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
                'moreInfo': '<a href="%s" target="_blank">Stackdriver Console</a>' % incident['url']
            },
            customer=incident.get('customer'),
            origin=incident.get('origin', 'Stackdriver'),
            event_type='stackdriverAlert',
            create_time=create_time,
            raw_data=payload
        )
