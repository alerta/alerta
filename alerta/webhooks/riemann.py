
from flask import request, g, jsonify
from flask_cors import cross_origin

from alerta.auth.utils import permission
from alerta.exceptions import ApiError, RejectException
from alerta.models.alert import Alert
from alerta.utils.api import process_alert, add_remote_ip
from . import webhooks


def parse_riemann(alert):

    return Alert(
        resource='%s-%s' % (alert['host'], alert['service']),
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

    if g.get('customer', None):
        incomingAlert.customer = g.get('customer')

    add_remote_ip(request, incomingAlert)

    try:
        alert = process_alert(incomingAlert)
    except RejectException as e:
        raise ApiError(str(e), 403)
    except Exception as e:
        raise ApiError(str(e), 500)

    if alert:
        return jsonify(status="ok", id=alert.id, alert=alert.serialize), 201
    else:
        raise ApiError("insert or update of Riemann alarm failed", 500)
