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


def parse_serverdensity(alert: JSON) -> Alert:

    if alert['fixed']:
        severity = 'ok'
    else:
        severity = 'critical'

    return Alert(
        resource=alert['item_name'],
        event=alert['alert_type'],
        environment='Production',
        severity=severity,
        service=[alert['item_type']],
        group=alert['alert_section'],
        value=alert['configured_trigger_value'],
        text='Alert created for {}:{}'.format(alert['item_type'], alert['item_name']),
        tags=['cloud'] if alert['item_cloud'] else [],
        attributes={
            'alertId': alert['alert_id'],
            'itemId': alert['item_id']
        },
        origin='ServerDensity',
        event_type='serverDensityAlert',
        raw_data=alert
    )


@webhooks.route('/webhooks/serverdensity', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission(Scope.write_webhooks)
def serverdensity():

    try:
        incomingAlert = parse_serverdensity(request.json)
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

    text = 'serverdensity alert received via webhook'
    write_audit_trail.send(current_app._get_current_object(), event='webhook-received', message=text, user=g.user,
                           customers=g.customers, scopes=g.scopes, resource_id=alert.id, type='alert', request=request)

    if alert:
        return jsonify(status='ok', id=alert.id, alert=alert.serialize), 201
    else:
        raise ApiError('insert or update of ServerDensity alert failed', 500)
