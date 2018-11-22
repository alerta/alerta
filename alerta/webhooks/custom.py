
from flask import current_app, g, jsonify, request
from flask_cors import cross_origin

from alerta.app import custom_webhooks
from alerta.auth.decorators import permission
from alerta.exceptions import ApiError, RejectException
from alerta.models.alert import Alert
from alerta.models.enums import Scope
from alerta.utils.api import add_remote_ip, assign_customer, process_alert
from alerta.utils.audit import write_audit_trail

from . import webhooks


@webhooks.route('/webhooks/<webhook>', methods=['OPTIONS', 'GET', 'POST'])
@cross_origin()
@permission(Scope.write_webhooks)
def custom(webhook):
    try:
        response = custom_webhooks.webhooks[webhook].incoming(
            query_string=request.args,
            payload=request.get_json() or request.get_data(as_text=True) or request.form
        )
    except KeyError as e:
        raise ApiError("Webhook '%s' not found. Did you mean to use POST instead of GET?" % webhook, 404)
    except ValueError as e:
        raise ApiError(str(e), 400)

    if isinstance(response, Alert):
        response.customer = assign_customer(wanted=response.customer)
        add_remote_ip(request, response)

        try:
            alert = process_alert(response)
        except RejectException as e:
            raise ApiError(str(e), 403)
        except Exception as e:
            raise ApiError(str(e), 500)

        text = '{} alert received via custom webhook'.format(webhook)
        write_audit_trail.send(current_app._get_current_object(), event='webhook-received', message=text, user=g.user,
                               customers=g.customers, scopes=g.scopes, resource_id=alert.id, type='alert',
                               request=request)
        if alert:
            return jsonify(status='ok', id=alert.id, alert=alert.serialize), 201
        else:
            raise ApiError('insert or update via %s webhook failed' % webhook, 500)
    else:
        text = '{} request received via custom webhook'.format(webhook)
        write_audit_trail.send(current_app._get_current_object(), event='webhook-received', message=text, user=g.user,
                               customers=g.customers, scopes=g.scopes, resource_id=None, type='user-defined',
                               request=request)
        return jsonify(**response)
