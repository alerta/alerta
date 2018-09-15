
from flask import jsonify, request
from flask_cors import cross_origin

from alerta.app import custom_webhooks
from alerta.auth.decorators import permission
from alerta.exceptions import ApiError, RejectException
from alerta.utils.api import add_remote_ip, assign_customer, process_alert

from . import webhooks


@webhooks.route('/webhooks/<webhook>', methods=['OPTIONS', 'GET', 'POST'])
@cross_origin()
@permission('write:webhooks')
def custom(webhook):
    try:
        incomingAlert = custom_webhooks.webhooks[webhook].incoming(
            query_string=request.args,
            payload=request.get_json() or request.get_data(as_text=True) or request.form
        )
    except KeyError as e:
        raise ApiError("Webhook '%s' not found. Did you mean to use POST instead of GET?" % webhook, 404)
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
        raise ApiError('insert or update via %s webhook failed' % webhook, 500)
