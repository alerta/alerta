from typing import Any, Dict

from alerta.models.alert import Alert

from . import WebhookBase

JSON = Dict[str, Any]


class PingdomWebhook(WebhookBase):
    """
    Pingdom state change webhook
    See https://www.pingdom.com/resources/webhooks/
    """

    def incoming(self, query_string, payload):

        if payload['importance_level'] == 'HIGH':
            severity = 'critical'
        else:
            severity = 'warning'

        if payload['current_state'] == 'UP':
            severity = 'normal'

        return Alert(
            resource=payload['check_name'],
            event=payload['current_state'],
            correlate=['UP', 'DOWN'],
            environment='Production',
            severity=severity,
            service=[payload['check_type']],
            group='Network',
            value=payload['description'],
            text='{}: {}'.format(payload['importance_level'], payload['long_description']),
            tags=payload['tags'],
            attributes={'checkId': payload['check_id']},
            origin='Pingdom',
            event_type='availabilityAlert',
            raw_data=payload
        )
