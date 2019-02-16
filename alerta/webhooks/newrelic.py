from typing import Any, Dict

from alerta.models.alert import Alert

from . import WebhookBase

JSON = Dict[str, Any]


class NewRelicWebhook(WebhookBase):
    """
    New Relic webhook notification channel
    See https://docs.newrelic.com/docs/alerts/new-relic-alerts/managing-notification-channels/notification-channels-control-where-send-alerts
    """

    def incoming(self, query_string, payload):

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

        attributes = dict()
        if 'incident_url' in payload:
            attributes['moreInfo'] = '<a href="%s" target="_blank">Incident URL</a>' % payload['incident_url']
        if 'runbook_url' in payload:
            attributes['runBook'] = '<a href="%s" target="_blank">Runbook URL</a>' % payload['runbook_url']

        return Alert(
            resource=payload['targets'][0]['name'],
            event=payload['condition_name'],
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
