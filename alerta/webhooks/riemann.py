from typing import Any, Dict

from alerta.models.alert import Alert

from . import WebhookBase

JSON = Dict[str, Any]


class RiemannWebhook(WebhookBase):
    """
    Riemann HTTP client
    http://riemann.io/clients.html
    """

    def incoming(self, path, query_string, payload):

        return Alert(
            resource='{}-{}'.format(payload['host'], payload['service']),
            event=payload.get('event', payload['service']),
            environment=payload.get('environment', 'Production'),
            severity=payload.get('state', 'unknown'),
            service=[payload['service']],
            group=payload.get('group', 'Performance'),
            text=payload.get('description', None),
            value=payload.get('metric', None),
            tags=payload.get('tags', None),
            origin='Riemann',
            raw_data=payload
        )
