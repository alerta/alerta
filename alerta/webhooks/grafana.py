
from flask import request, g, jsonify
from flask_cors import cross_origin

from alerta.app import qb
from alerta.auth.utils import permission
from alerta.exceptions import RejectException, ApiError
from alerta.models.alert import Alert
from alerta.utils.api import process_alert, add_remote_ip
from . import webhooks


def parse_grafana(alert, match):

    if alert['state'] == 'alerting':
        severity = 'major'
    elif alert['state'] == 'ok':
        severity = 'normal'
    else:
        severity = 'indeterminate'

    attributes = match.get('tags', None) or dict()
    attributes['ruleId'] = str(alert['ruleId'])
    if 'ruleUrl' in alert:
        attributes['ruleUrl'] = '<a href="%s" target="_blank">Rule</a>' % alert['ruleUrl']
    if 'imageUrl' in alert:
        attributes['imageUrl'] = '<a href="%s" target="_blank">Image</a>' % alert['imageUrl']

    return Alert(
        resource=match['metric'],
        event=alert['ruleName'],
        environment='Production',
        severity=severity,
        service=['Grafana'],
        group='Performance',
        value='%s' % match['value'],
        text=alert.get('message', None) or alert.get('title', alert['state']),
        tags=list(),
        attributes=attributes,
        origin='Grafana',
        event_type='performanceAlert',
        timeout=300,
        raw_data=alert
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
                incomingAlert = parse_grafana(data, match)
            except ValueError as e:
                return jsonify(status="error", message=str(e)), 400

            if g.get('customer', None):
                incomingAlert.customer = g.get('customer')

            add_remote_ip(request, incomingAlert)

            try:
                alert = process_alert(incomingAlert)
            except RejectException as e:
                return jsonify(status="error", message=str(e)), 403
            except Exception as e:
                return jsonify(status="error", message=str(e)), 500
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
        raise ApiError("no alerts in Grafana notification payload", 400)

    if len(alerts) == 1:
        return jsonify(status="ok", id=alerts[0].id, alert=alerts[0].serialize), 201
    else:
        return jsonify(status="ok", ids=[alert.id for alert in alerts]), 201
