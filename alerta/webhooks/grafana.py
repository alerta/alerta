import json
from typing import Any, Dict

from flask import current_app, jsonify, request
from flask_cors import cross_origin
from werkzeug.datastructures import ImmutableMultiDict

from alerta.app import qb
from alerta.auth.decorators import permission
from alerta.exceptions import ApiError, RejectException
from alerta.models.alert import Alert
from alerta.utils.api import add_remote_ip, assign_customer, process_alert

from . import webhooks

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
    timeout = args.get('timeout', current_app.config['ALERT_TIMEOUT'])

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


@webhooks.route('/webhooks/grafana', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission('write:webhooks')
def grafana():

    alerts = []
    data = request.json
    if data and data['state'] == 'alerting':
        for match in data.get('evalMatches', []):
            try:
                incomingAlert = parse_grafana(data, match, request.args)
            except ValueError as e:
                return jsonify(status='error', message=str(e)), 400

            incomingAlert.customer = assign_customer(wanted=incomingAlert.customer)
            add_remote_ip(request, incomingAlert)

            try:
                alert = process_alert(incomingAlert)
            except RejectException as e:
                return jsonify(status='error', message=str(e)), 403
            except Exception as e:
                return jsonify(status='error', message=str(e)), 500
            alerts.append(alert)

    elif data and data['state'] == 'ok' and data.get('ruleId', None):
        try:
            query = qb.from_dict({'attributes.ruleId': str(data['ruleId'])})
            existingAlerts = Alert.find_all(query)
        except Exception as e:
            raise ApiError(str(e), 500)

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
    else:
        raise ApiError('no alerts in Grafana notification payload', 400)

    if len(alerts) == 1:
        return jsonify(status='ok', id=alerts[0].id, alert=alerts[0].serialize), 201
    else:
        return jsonify(status='ok', ids=[alert.id for alert in alerts]), 201
