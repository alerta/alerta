
from datetime import datetime

from flask import request, g, jsonify
from flask_cors import cross_origin

from alerta.auth.utils import permission
from alerta.exceptions import ApiError, RejectException
from alerta.models.alert import Alert
from alerta.utils.api import process_alert, add_remote_ip
from . import webhooks


def parse_stackdriver(notification):

    incident = notification['incident']
    state = incident['state']

    if state == 'open':
        severity = 'critical'
        status = None
        create_time = datetime.fromtimestamp(incident['started_at'])
    elif state == 'acknowledged':
        severity = 'critical'
        status = 'ack'
        create_time = None
    elif state == 'closed':
        severity = 'ok'
        status = None
        create_time = datetime.fromtimestamp(incident['ended_at'])
    else:
        severity = 'indeterminate'
        status = None
        create_time = None

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
@permission('write:webhooks')
def stackdriver():

    try:
        incomingAlert = parse_stackdriver(request.get_json(force=True))
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
        raise ApiError("insert or update of StackDriver notification failed", 500)
