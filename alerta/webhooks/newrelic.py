from typing import Any, Dict

from alerta.models.alarms.alerta import SEVERITY_MAP
from alerta.models.alert import Alert

from . import WebhookBase

JSON = Dict[str, Any]
UNKNOWN = 'unknown'


class NewRelicWebhook(WebhookBase):

    """
    New Relic webhook notification channel
    See https://docs.newrelic.com/docs/alerts/new-relic-alerts/managing-notification-channels/notification-channels-control-where-send-alerts
    """

    def incoming(self, path, query_string, payload):

        if 'version' not in payload:
            raise ValueError('New Relic Legacy Alerting is not supported')

        status = payload['current_state'].lower()
        if status == 'open':
            severity = payload['severity'].lower()
        elif status == 'acknowledged':
            severity = payload['severity'].lower()
            status = 'ack'
        elif status == 'closed':
            severity = 'ok'
        elif payload['severity'].lower() == 'info':
            severity = 'informational'
            status = 'open'
        else:
            severity = payload['severity'].lower()
            status = 'open'

        if severity not in SEVERITY_MAP:
            if severity.lower() == 'info':
                severity = 'informational'
            else:
                severity = 'unknown'

        attributes = dict()
        if 'incident_url' in payload and payload['incident_url'] is not None:
            attributes['incident_url'] = payload['incident_url']
        if 'runbook_url' in payload and payload['runbook_url'] is not None:
            attributes['runbook_url'] = payload['runbook_url']

        resource = payload['targets'][0]['name'] or UNKNOWN
        event = payload['condition_name'] or UNKNOWN

        return Alert(
            resource=resource,
            event=event,
            environment='Production',
            severity=severity,
            status=status,
            service=[payload['account_name']],
            group=payload['targets'][0]['type'],
            text=payload['details'],
            tags=['{}:{}'.format(key, value) for (key, value) in payload['targets'][0]['labels'].items()],
            attributes=attributes,
            origin='New Relic/v%s' % payload['version'],
            event_type=payload['event_type'].lower(),
            raw_data=payload
        )
