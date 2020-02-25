import datetime
from typing import Any, Dict

from alerta.app import alarm_model
from alerta.exceptions import ApiError
from alerta.models.alert import Alert

from . import WebhookBase

JSON = Dict[str, Any]
dt = datetime.datetime


def parse_prometheus(alert: JSON, external_url: str) -> Alert:

    status = alert.get('status', 'firing')

    # Allow labels and annotations to use python string formats that refer to
    # other labels eg. runbook = 'https://internal.myorg.net/wiki/alerts/{app}/{alertname}'
    # See https://github.com/prometheus/prometheus/issues/2818

    labels = {}
    for k, v in alert['labels'].items():
        try:
            labels[k] = v.format(**alert['labels'])
        except Exception:
            labels[k] = v

    annotations = {}
    for k, v in alert['annotations'].items():
        try:
            annotations[k] = v.format(**labels)
        except Exception:
            annotations[k] = v

    if status == 'firing':
        severity = labels.pop('severity', 'warning')
    elif status == 'resolved':
        severity = alarm_model.DEFAULT_NORMAL_SEVERITY
    else:
        severity = 'unknown'

    # labels
    resource = labels.pop('exported_instance', None) or labels.pop('instance', 'n/a')
    event = labels.pop('event', None) or labels.pop('alertname')
    environment = labels.pop('environment', 'Production')
    customer = labels.pop('customer', None)
    correlate = labels.pop('correlate').split(',') if 'correlate' in labels else None
    service = labels.pop('service', '').split(',')
    group = labels.pop('group', None) or labels.pop('job', 'Prometheus')
    origin = 'prometheus/' + labels.pop('monitor', '-')
    tags = ['{}={}'.format(k, v) for k, v in labels.items()]  # any labels left over are used for tags

    try:
        timeout = int(labels.pop('timeout', 0)) or None
    except ValueError:
        timeout = None

    # annotations
    value = annotations.pop('value', None)
    summary = annotations.pop('summary', None)
    description = annotations.pop('description', None)
    text = description or summary or '{}: {} is {}'.format(severity.upper(), resource, event)

    if external_url:
        annotations['externalUrl'] = external_url  # needed as raw URL for bi-directional integration
    if 'generatorURL' in alert:
        annotations['moreInfo'] = '<a href="{}" target="_blank">Prometheus Graph</a>'.format(alert['generatorURL'])

    # attributes
    attributes = {
        'startsAt': alert['startsAt'],
        'endsAt': alert['endsAt']
    }
    attributes.update(annotations)  # any annotations left over are used for attributes

    return Alert(
        resource=resource,
        event=event,
        environment=environment,
        customer=customer,
        severity=severity,
        correlate=correlate,
        service=service,
        group=group,
        value=value,
        text=text,
        attributes=attributes,
        origin=origin,
        event_type='prometheusAlert',
        timeout=timeout,
        raw_data=alert,
        tags=tags
    )


class PrometheusWebhook(WebhookBase):
    """
    Prometheus Alertmanager webhook receiver
    See https://prometheus.io/docs/operating/integrations/#alertmanager-webhook-receiver
    """

    def incoming(self, path, query_string, payload):

        if payload and 'alerts' in payload:
            external_url = payload.get('externalURL')
            return [parse_prometheus(alert, external_url) for alert in payload['alerts']]
        else:
            raise ApiError('no alerts in Prometheus notification payload', 400)
