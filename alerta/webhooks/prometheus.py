
from copy import copy

import pytz
from dateutil.parser import parse as parse_date
from flask import request, g, jsonify
from flask_cors import cross_origin

from alerta.auth.utils import permission
from alerta.exceptions import RejectException, ApiError
from alerta.models.alert import Alert
from alerta.utils.api import process_alert, add_remote_ip
from . import webhooks


def parse_prometheus(alert, external_url):

    status = alert.get('status', 'firing')

    labels = copy(alert['labels'])
    annotations = copy(alert['annotations'])

    starts_at = parse_date(alert['startsAt'])
    if alert['endsAt'] == '0001-01-01T00:00:00Z':
        ends_at = None
    else:
        ends_at = parse_date(alert['endsAt'])

    if status == 'firing':
        severity = labels.pop('severity', 'warning')
        create_time = starts_at
    elif status == 'resolved':
        severity = 'normal'
        create_time = ends_at
    else:
        severity = 'unknown'
        create_time = ends_at or starts_at

    summary = annotations.pop('summary', None)
    description = annotations.pop('description', None)
    text = description or summary or '%s: %s on %s' % (labels['job'], labels['alertname'], labels['instance'])

    try:
        timeout = int(labels.pop('timeout', 0)) or None
    except ValueError:
        timeout = None

    if external_url:
        annotations['externalUrl'] = external_url
    if 'generatorURL' in alert:
        annotations['moreInfo'] = '<a href="%s" target="_blank">Prometheus Graph</a>' % alert['generatorURL']

    return Alert(
        resource=labels.pop('exported_instance', None) or labels.pop('instance', 'n/a'),
        event=labels.pop('alertname'),
        environment=labels.pop('environment', 'Production'),
        severity=severity,
        correlate=labels.pop('correlate').split(',') if 'correlate' in labels else None,
        service=labels.pop('service', '').split(','),
        group=labels.pop('job', 'Prometheus'),
        value=labels.pop('value', None),
        text=text,
        attributes=annotations,
        origin='prometheus/' + labels.pop('monitor', '-'),
        event_type='prometheusAlert',
        create_time=create_time.astimezone(tz=pytz.UTC).replace(tzinfo=None),
        timeout=timeout,
        raw_data=alert,
        tags=["%s=%s" % t for t in labels.items()]  # any labels left are used for tags
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

            if g.get('customer', None):
                incomingAlert.customer = g.get('customer')

            add_remote_ip(request, incomingAlert)

            try:
                alert = process_alert(incomingAlert)
            except RejectException as e:
                raise ApiError(str(e), 403)
            except Exception as e:
                raise ApiError(str(e), 500)
            alerts.append(alert)
    else:
        raise ApiError("no alerts in Prometheus notification payload", 400)

    if len(alerts) == 1:
        return jsonify(status="ok", id=alerts[0].id, alert=alerts[0].serialize), 201
    else:
        return jsonify(status="ok", ids=[alert.id for alert in alerts]), 201
