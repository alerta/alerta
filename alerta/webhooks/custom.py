
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
    if webhook not in custom_webhooks.webhooks:
        raise ApiError("Custom webhook '%s' not found." % webhook, 404)

    try:
        rv = custom_webhooks.webhooks[webhook].incoming(
            query_string=request.args,
            payload=request.get_json() or request.get_data(as_text=True) or request.form
        )
    except Exception as e:
        raise ApiError(str(e), 400)

    if isinstance(rv, Alert):
        rv = [rv]

    if isinstance(rv, list):
        alerts = []
        for alert in rv:
            alert.customer = assign_customer(wanted=alert.customer)
            add_remote_ip(request, alert)

            try:
                alert = process_alert(alert)
            except RejectException as e:
                raise ApiError(str(e), 403)
            except Exception as e:
                raise ApiError(str(e), 500)

            text = 'alert received via {} webhook'.format(webhook)
            write_audit_trail.send(current_app._get_current_object(), event='webhook-received', message=text,
                                   user=g.user, customers=g.customers, scopes=g.scopes, resource_id=alert.id,
                                   type='alert', request=request)
            alerts.append(alert)

        if len(alerts) == 1:
            return jsonify(status='ok', id=alerts[0].id, alert=alerts[0].serialize), 201
        else:
            return jsonify(status='ok', ids=[alert.id for alert in alerts]), 201

    else:
        text = 'request received via {} webhook'.format(webhook)
        write_audit_trail.send(current_app._get_current_object(), event='webhook-received', message=text, user=g.user,
                               customers=g.customers, scopes=g.scopes, resource_id=None, type='user-defined',
                               request=request)
        return rv
