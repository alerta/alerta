from typing import Any, Dict

from flask import jsonify, request
from flask_cors import cross_origin

from alerta.auth.decorators import permission
from alerta.exceptions import ApiError, RejectException
from alerta.models.alert import Alert
from alerta.utils.api import add_remote_ip, assign_customer, process_alert

from . import webhooks

# {
#     "second_probe": {},
#     "check_type": "HTTP",
#     "first_probe": {},
#     "tags": [],
#     "check_id": 803318,
#     "current_state": "DOWN",
#     "check_params": {
#         "url": "/",
#         "encryption": false,
#         "hostname": "api.alerta.io",
#         "basic_auth": false,
#         "port": 80,
#         "header": "User-Agent:Pingdom.com_bot_version_1.4_(http://www.pingdom.com/)",
#         "ipv6": false,
#         "full_url": "http://api.alerta.io/"
#     },
#     "previous_state": "UP",
#     "check_name": "Alerta API on OpenShift",
#     "version": 1,
#     "state_changed_timestamp": 1498859836,
#     "importance_level": "HIGH",
#     "state_changed_utc_time": "2017-06-30T21:57:16",
#     "long_description": "This is a test message triggered by a user in My Pingdom",
#     "description": "test"
# }

JSON = Dict[str, Any]


def parse_pingdom(check: JSON) -> Alert:

    if check['importance_level'] == 'HIGH':
        severity = 'critical'
    else:
        severity = 'warning'

    if check['current_state'] == 'UP':
        severity = 'normal'

    return Alert(
        resource=check['check_name'],
        event=check['current_state'],
        correlate=['UP', 'DOWN'],
        environment='Production',
        severity=severity,
        service=[check['check_type']],
        group='Network',
        value=check['description'],
        text='{}: {}'.format(check['importance_level'], check['long_description']),
        tags=check['tags'],
        attributes={'checkId': check['check_id']},
        origin='Pingdom',
        event_type='availabilityAlert',
        raw_data=check
    )


@webhooks.route('/webhooks/pingdom', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission('write:webhooks')
def pingdom():

    try:
        incomingAlert = parse_pingdom(request.json)
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
        raise ApiError('insert or update of pingdom check failed', 500)
