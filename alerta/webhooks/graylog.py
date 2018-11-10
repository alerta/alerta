from typing import Any, Dict

from flask import current_app, g, jsonify, request
from flask_cors import cross_origin

from alerta.auth.decorators import permission
from alerta.exceptions import ApiError, RejectException
from alerta.models.alert import Alert
from alerta.models.enums import Scope
from alerta.utils.api import add_remote_ip, assign_customer, process_alert
from alerta.utils.audit import write_audit_trail

from . import webhooks

JSON = Dict[str, Any]


def parse_graylog(alert: JSON) -> Alert:

    return Alert(
        resource=alert['stream']['title'],
        event='Alert',
        environment='Development',
        service=['test'],
        severity='critical',
        value='n/a',
        text=alert['check_result']['result_description'],
        attributes={'checkId': alert['check_result']['triggered_condition']['id']},
        origin='Graylog',
        event_type='performanceAlert',
        raw_data=alert)


@webhooks.route('/webhooks/graylog', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission(Scope.write_webhooks)
def graylog():

    try:
        incomingAlert = parse_graylog(request.json)
    except ValueError as e:
        raise ApiError(str(e), 400)

    if request.args.get('event', None):
        incomingAlert.event = request.args.get('event')
    if request.args.get('event_type', None):
        incomingAlert.event_type = request.args.get('event_type')
    if request.args.get('environment', None):
        incomingAlert.environment = request.args.get('environment')
    if request.args.get('service', None):
        incomingAlert.service = request.args.get('service').split(',')
    if request.args.get('severity', None):
        incomingAlert.severity = request.args.get('severity')

    incomingAlert.customer = assign_customer(wanted=incomingAlert.customer)
    add_remote_ip(request, incomingAlert)

    try:
        alert = process_alert(incomingAlert)
    except RejectException as e:
        raise ApiError(str(e), 403)
    except Exception as e:
        raise ApiError(str(e), 500)

    text = 'graylog alert received via webhook'
    write_audit_trail.send(current_app._get_current_object(), event='webhook-received', message=text, user=g.user,
                           customers=g.customers, scopes=g.scopes, resource_id=alert.id, type='alert', request=request)

    if alert:
        return jsonify(status='ok', id=alert.id, alert=alert.serialize), 201
    else:
        raise ApiError('insert or update of graylog check failed', 500)
