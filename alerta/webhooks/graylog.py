from typing import Any, Dict

from alerta.models.alert import Alert

from . import WebhookBase

JSON = Dict[str, Any]


class GraylogWebhook(WebhookBase):
    """
    Graylog Log Management HTTP alert notifications
    See http://docs.graylog.org/en/3.0/pages/streams/alerts.html#http-alert-notification
    """

    def incoming(self, query_string, payload):

        return Alert(
            resource=payload['stream']['title'],
            event=query_string.get('event', 'Alert'),
            environment=query_string.get('environment', 'Development'),
            service=query_string.get('service', 'test').split(','),
            severity=query_string.get('severity', 'critical'),
            value='n/a',
            text=payload['check_result']['result_description'],
            attributes={'checkId': payload['check_result']['triggered_condition']['id']},
            origin='Graylog',
            event_type=query_string.get('event_type', 'performanceAlert'),
            raw_data=payload)
