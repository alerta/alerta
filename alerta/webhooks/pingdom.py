from typing import Any, Dict

from alerta.app import alarm_model
from alerta.models.alert import Alert

from . import WebhookBase

JSON = Dict[str, Any]


class PingdomWebhook(WebhookBase):
    """
    Pingdom state change webhook
    See https://www.pingdom.com/resources/webhooks/
    """

    def incoming(self, path, query_string, payload):

        # Default values
        environment = 'Production'
        group = 'Network'

        if payload['importance_level'] == 'HIGH':
            severity = 'critical'
        else:
            severity = 'warning'

        if payload['current_state'] == 'UP':
            severity = alarm_model.DEFAULT_NORMAL_SEVERITY

        if len(payload['tags']) > 0:
            tags_dict = { d[0].strip():d[1].strip() for d in [ t.split(':') for t in payload['tags'] if ':' in t ] }

            if 'environment' in tags_dict:
                environment = tags_dict['environment']

            if 'group' in tags_dict:
                group = tags_dict['group']

        return Alert(
            resource=payload['check_name'],
            event=payload['current_state'],
            correlate=['UP', 'DOWN'],
            environment=environment,
            severity=severity,
            service=[payload['check_type']],
            group=group,
            value=payload['description'],
            text='{}: {}'.format(payload['importance_level'], payload['long_description']),
            tags=payload['tags'],
            attributes={'checkId': payload['check_id']},
            origin='Pingdom',
            event_type='availabilityAlert',
            raw_data=payload
        )
