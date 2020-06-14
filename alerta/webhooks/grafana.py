import json
from typing import Any, Dict

from werkzeug.datastructures import ImmutableMultiDict

from alerta.app import alarm_model, qb
from alerta.exceptions import ApiError, RejectException
from alerta.models.alert import Alert
from alerta.utils.api import process_alert

from . import WebhookBase

JSON = Dict[str, Any]


def parse_grafana(args: ImmutableMultiDict, alert: JSON, match: Dict[str, Any]) -> Alert:

    # get values from request params
    environment = args.get('environment', 'Production')
    alerting_severity = args.get('severity', 'major')
    service = args.getlist('service') or ['Grafana']
    group = args.get('group', 'Performance')
    customer = args.get('customer', None)
    origin = args.get('origin', 'Grafana')
    timeout = args.get('timeout', type=int)

    # get metric labels (evalMatches tags)
    match_tags = match.get('tags') or {}
    environment = match_tags.pop('environment', environment)
    alerting_severity = match_tags.pop('severity', alerting_severity)
    if 'service' in match_tags:
        service.append(match_tags.pop('service'))
    group = match_tags.pop('group', group)
    customer = match_tags.pop('customer', customer)
    origin = match_tags.pop('origin', origin)

    # assign leftover match tags as attributes
    attributes = {k.replace('.', '_'): v for (k, v) in match_tags.items()}

    # get alert rule tags
    rules_tags = alert.get('tags') or {}
    environment = rules_tags.pop('environment', environment)
    alerting_severity = rules_tags.pop('severity', alerting_severity)
    if 'service' in rules_tags:
        service.append(rules_tags.pop('service'))
    group = rules_tags.pop('group', group)
    customer = rules_tags.pop('customer', customer)
    origin = rules_tags.pop('origin', origin)

    # set severity
    if alert['state'] == 'alerting':
        severity = alerting_severity
    elif alert['state'] == 'ok':
        severity = alarm_model.DEFAULT_NORMAL_SEVERITY
    else:
        severity = 'indeterminate'

    # assign leftover rule tags as attributes
    attributes.update({k.replace('.', '_'): v for (k, v) in rules_tags.items()})

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
        service=service,
        group=group,
        value='%s' % match['value'],
        text=alert.get('message', None) or alert.get('title', alert['state']),
        tags=list(),
        attributes=attributes,
        customer=customer,
        origin=origin,
        event_type='grafanaAlert',
        timeout=timeout,
        raw_data=json.dumps(alert)
    )


class GrafanaWebhook(WebhookBase):
    """
    Grafana Alert alert notification webhook
    See http://docs.grafana.org/alerting/notifications/#webhook
    """

    def incoming(self, path, query_string, payload):

        if payload and payload['state'] == 'alerting':
            return [parse_grafana(query_string, payload, match) for match in payload.get('evalMatches', [])]

        elif payload and payload['state'] == 'ok' and payload.get('ruleId'):
            try:
                query = qb.from_dict({'attributes.ruleId': str(payload['ruleId'])})
                existingAlerts = Alert.find_all(query)
            except Exception as e:
                raise ApiError(str(e), 500)

            alerts = []
            for updateAlert in existingAlerts:
                updateAlert.severity = alarm_model.DEFAULT_NORMAL_SEVERITY
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
