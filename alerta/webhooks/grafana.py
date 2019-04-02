import json
from typing import Any, Dict

from werkzeug.datastructures import ImmutableMultiDict

from alerta.app import qb
from alerta.exceptions import ApiError, RejectException
from alerta.models.alert import Alert
from alerta.utils.api import process_alert

from . import WebhookBase

JSON = Dict[str, Any]


def parse_grafana(alert: JSON, match: Dict[str, Any], args: ImmutableMultiDict) -> Alert:
    alerting_severity = args.get('severity', 'major')

    if alert['state'] == 'alerting':
        severity = alerting_severity
    elif alert['state'] == 'ok':
        severity = 'normal'
    else:
        severity = 'indeterminate'

    environment = args.get('environment', 'Production')  # TODO: verify at create?
    event_type = args.get('event_type', 'performanceAlert')
    group = args.get('group', 'Performance')
    origin = args.get('origin', 'Grafana')
    service = args.get('service', 'Grafana')
    timeout = args.get('timeout', type=int)

    attributes = match.get('tags', None) or dict()
    attributes = {k.replace('.', '_'): v for (k, v) in attributes.items()}

    attributes['ruleId'] = str(alert['ruleId'])
    if 'ruleUrl' in alert:
        attributes['ruleUrl'] = '<a href="%s" target="_blank">Rule</a>' % alert['ruleUrl']
    if 'imageUrl' in alert:
        attributes['imageUrl'] = '<a href="%s" target="_blank">Image</a>' % alert['imageUrl']

    return Alert(
        resource=match['metric'],
        event=alert['ruleName'],
        environment=environment,
        severity=severity,
        service=[service],
        group=group,
        value='%s' % match['value'],
        text=alert.get('message', None) or alert.get('title', alert['state']),
        tags=list(),
        attributes=attributes,
        origin=origin,
        event_type=event_type,
        timeout=timeout,
        raw_data=json.dumps(alert)
    )


class GrafanaWebhook(WebhookBase):
    """
    Grafana Alert alert notification webhook
    See http://docs.grafana.org/alerting/notifications/#webhook
    """

    def incoming(self, query_string, payload):

        if payload and payload['state'] == 'alerting':
            return [parse_grafana(payload, match, query_string) for match in payload.get('evalMatches', [])]

        elif payload and payload['state'] == 'ok' and payload.get('ruleId'):
            try:
                query = qb.from_dict({'attributes.ruleId': str(payload['ruleId'])})
                existingAlerts = Alert.find_all(query)
            except Exception as e:
                raise ApiError(str(e), 500)

            alerts = []
            for updateAlert in existingAlerts:
                updateAlert.severity = 'normal'
                updateAlert.status = 'closed'

                try:
                    alert = process_alert(updateAlert)
                except RejectException as e:
                    raise ApiError(str(e), 403)
                except Exception as e:
                    raise ApiError(str(e), 500)
                alerts.append(alert)
            return alerts
        else:
            raise ApiError('no alerts in Grafana notification payload', 400)
