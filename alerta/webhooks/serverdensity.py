from typing import Any, Dict

from alerta.models.alert import Alert

from . import WebhookBase

JSON = Dict[str, Any]


class ServerDensityWebhook(WebhookBase):
    """
    Server Density notification webhook
    See https://support.serverdensity.com/hc/en-us/articles/360001067183-Setting-up-webhooks
    """

    def incoming(self, query_string, payload):

        if payload['fixed']:
            severity = 'ok'
        else:
            severity = 'critical'

        return Alert(
            resource=payload['item_name'],
            event=payload['alert_type'],
            environment='Production',
            severity=severity,
            service=[payload['item_type']],
            group=payload['alert_section'],
            value=payload['configured_trigger_value'],
            text='Alert created for {}:{}'.format(payload['item_type'], payload['item_name']),
            tags=['cloud'] if payload['item_cloud'] else [],
            attributes={
                'alertId': payload['alert_id'],
                'itemId': payload['item_id']
            },
            origin='ServerDensity',
            event_type='serverDensityAlert',
            raw_data=payload
        )
