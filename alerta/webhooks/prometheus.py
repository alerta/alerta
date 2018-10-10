
import datetime
from copy import copy
from typing import Any, Dict

import pytz
from dateutil.parser import parse as parse_date
from flask import jsonify, request
from flask_cors import cross_origin

from alerta.auth.decorators import permission
from alerta.exceptions import ApiError, RejectException
from alerta.models.alert import Alert
from alerta.utils.api import add_remote_ip, assign_customer, process_alert

from . import webhooks

JSON = Dict[str, Any]
dt = datetime.datetime


def parse_prometheus(alert: JSON, external_url: str) -> Alert:

    status = alert.get('status', 'firing')

    labels = copy(alert['labels'])
    annotations = copy(alert['annotations'])

    starts_at = parse_date(alert['startsAt'])
    if alert['endsAt'] != '0001-01-01T00:00:00Z':
        ends_at = parse_date(alert['endsAt'])
    else:
        ends_at = None  # type: ignore

    if status == 'firing':
        severity = labels.pop('severity', 'warning')
        create_time = starts_at
    elif status == 'resolved':
        severity = 'normal'
        create_time = ends_at
    else:
        severity = 'unknown'
        create_time = ends_at or starts_at

    # labels
    resource = labels.pop('exported_instance', None) or labels.pop('instance', 'n/a')
    event = labels.pop('alertname')
    environment = labels.pop('environment', 'Production')
    correlate = labels.pop('correlate').split(',') if 'correlate' in labels else None
    service = labels.pop('service', '').split(',')
    group = labels.pop('job', 'Prometheus')
    origin = 'prometheus/' + labels.pop('monitor', '-')
    tags = ['%s=%s' % t for t in labels.items()]  # any labels left over are used for tags

    try:
        timeout = int(labels.pop('timeout', 0)) or None
    except ValueError:
        timeout = None

    # annotations
    value = annotations.pop('value', None)
    summary = annotations.pop('summary', None)
    description = annotations.pop('description', None)
    text = description or summary or '{}: {} is {}'.format(severity.upper(), resource, event)
    attributes = annotations  # any annotations left over are used for attributes

    if external_url:
        annotations['externalUrl'] = '<a href="%s" target="_blank">Open in Alertmanager</a>' % external_url
    if 'generatorURL' in alert:
        annotations['moreInfo'] = '<a href="%s" target="_blank">Prometheus Graph</a>' % alert['generatorURL']

    return Alert(
        resource=resource,
        event=event,
        environment=environment,
        severity=severity,
        correlate=correlate,
        service=service,
        group=group,
        value=value,
        text=text,
        attributes=attributes,
        origin=origin,
        event_type='prometheusAlert',
        create_time=create_time.astimezone(tz=pytz.UTC).replace(tzinfo=None),
        timeout=timeout,
        raw_data=alert,
        tags=tags
    )


@webhooks.route('/webhooks/prometheus', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission('write:webhooks')
def prometheus():

    alerts = []
    if request.json and 'alerts' in request.json:
        external_url = request.json.get('externalURL', None)
        for alert in request.json['alerts']:
            try:
                incomingAlert = parse_prometheus(alert, external_url)
            except ValueError as e:
                raise ApiError(str(e), 400)

            incomingAlert.customer = assign_customer(wanted=incomingAlert.customer)
            add_remote_ip(request, incomingAlert)

            try:
                alert = process_alert(incomingAlert)
            except RejectException as e:
                raise ApiError(str(e), 403)
            except Exception as e:
                raise ApiError(str(e), 500)
            alerts.append(alert)
    else:
        raise ApiError('no alerts in Prometheus notification payload', 400)

    if len(alerts) == 1:
        return jsonify(status='ok', id=alerts[0].id, alert=alerts[0].serialize), 201
    else:
        return jsonify(status='ok', ids=[alert.id for alert in alerts]), 201
