from typing import Any, Dict

from flask import jsonify, request
from flask_cors import cross_origin

from alerta.auth.decorators import permission
from alerta.exceptions import ApiError, RejectException
from alerta.models.alert import Alert
from alerta.utils.api import add_remote_ip, assign_customer, process_alert

from . import webhooks

JSON = Dict[str, Any]


def parse_riemann(alert: JSON) -> Alert:

    return Alert(
        resource='{}-{}'.format(alert['host'], alert['service']),
        event=alert.get('event', alert['service']),
        environment=alert.get('environment', 'Production'),
        severity=alert.get('state', 'unknown'),
        service=[alert['service']],
        group=alert.get('group', 'Performance'),
        text=alert.get('description', None),
        value=alert.get('metric', None),
        tags=alert.get('tags', None),
        origin='Riemann',
        raw_data=alert
    )


@webhooks.route('/webhooks/riemann', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission('write:webhooks')
def riemann():

    try:
        incomingAlert = parse_riemann(request.json)
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

    if alert:
        return jsonify(status='ok', id=alert.id, alert=alert.serialize), 201
    else:
        raise ApiError('insert or update of Riemann alarm failed', 500)
