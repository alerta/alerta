
from datetime import datetime
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


def parse_stackdriver(notification: JSON) -> Alert:

    incident = notification['incident']
    state = incident['state']

    if state == 'open':
        severity = 'critical'
        status = None
        create_time = datetime.fromtimestamp(incident['started_at'])
    elif state == 'acknowledged':
        severity = 'critical'
        status = 'ack'
        create_time = None  # type: ignore
    elif state == 'closed':
        severity = 'ok'
        status = None
        create_time = datetime.fromtimestamp(incident['ended_at'])
    else:
        severity = 'indeterminate'
        status = None
        create_time = None  # type: ignore

    return Alert(
        resource=incident['resource_name'],
        event=incident['condition_name'],
        environment='Production',
        severity=severity,
        status=status,
        service=[incident['policy_name']],
        group='Cloud',
        text=incident['summary'],
        attributes={
            'incidentId': incident['incident_id'],
            'resourceId': incident['resource_id'],
            'moreInfo': '<a href="%s" target="_blank">Stackdriver Console</a>' % incident['url']
        },
        origin='Stackdriver',
        event_type='stackdriverAlert',
        create_time=create_time,
        raw_data=notification
    )


@webhooks.route('/webhooks/stackdriver', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission(Scope.write_webhooks)
def stackdriver():

    try:
        incomingAlert = parse_stackdriver(request.get_json(force=True))
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

    text = 'stackdriver alert received via webhook'
    write_audit_trail.send(current_app._get_current_object(), event='webhook-received', message=text, user=g.user,
                           customers=g.customers, scopes=g.scopes, resource_id=alert.id, type='alert', request=request)

    if alert:
        return jsonify(status='ok', id=alert.id, alert=alert.serialize), 201
    else:
        raise ApiError('insert or update of StackDriver notification failed', 500)
