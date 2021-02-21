from flask import current_app, g, jsonify, request
from flask_cors import cross_origin

from alerta.app import custom_webhooks
from alerta.auth.decorators import permission
from alerta.exceptions import (AlertaException, ApiError, BlackoutPeriod,
                               ForwardingLoop, HeartbeatReceived, RateLimit,
                               RejectException)
from alerta.models.alert import Alert
from alerta.models.enums import Scope
from alerta.utils.api import assign_customer, process_alert
from alerta.utils.audit import write_audit_trail

from . import webhooks


@webhooks.route('/webhooks/<webhook>', defaults={'path': ''}, methods=['OPTIONS', 'GET', 'POST'])
@webhooks.route('/webhooks/<webhook>/<path:path>', methods=['OPTIONS', 'GET', 'POST'])
@cross_origin()
@permission(Scope.write_webhooks)
def custom(webhook, path):
    if webhook not in custom_webhooks.webhooks:
        raise ApiError("Custom webhook '%s' not found." % webhook, 404)

    try:
        rv = custom_webhooks.webhooks[webhook].incoming(
            path=path or request.path,
            query_string=request.args,
            payload=request.get_json() or request.form or request.get_data(as_text=True)
        )
    except TypeError:
        rv = custom_webhooks.webhooks[webhook].incoming(
            query_string=request.args,
            payload=request.get_json() or request.form or request.get_data(as_text=True)
        )
    except AlertaException as e:
        raise ApiError(e.message, code=e.code, errors=e.errors)
    except Exception as e:
        raise ApiError(str(e), 400)

    if isinstance(rv, Alert):
        rv = [rv]

    if isinstance(rv, list):
        alerts = []
        for alert in rv:
            alert.customer = assign_customer(wanted=alert.customer)

            def audit_trail_alert(event: str):
                write_audit_trail.send(current_app._get_current_object(), event=event, message=alert.text, user=g.login,
                                       customers=g.customers, scopes=g.scopes, resource_id=alert.id, type='alert',
                                       request=request)

            try:
                alert = process_alert(alert)
            except RejectException as e:
                audit_trail_alert(event='alert-rejected')
                raise ApiError(str(e), 403)
            except RateLimit as e:
                audit_trail_alert(event='alert-rate-limited')
                return jsonify(status='error', message=str(e), id=alert.id), 429
            except HeartbeatReceived as heartbeat:
                audit_trail_alert(event='alert-heartbeat')
                return jsonify(status='ok', message=str(heartbeat), id=heartbeat.id), 202
            except BlackoutPeriod as e:
                audit_trail_alert(event='alert-blackout')
                return jsonify(status='ok', message=str(e), id=alert.id), 202
            except ForwardingLoop as e:
                return jsonify(status='ok', message=str(e)), 202
            except AlertaException as e:
                raise ApiError(e.message, code=e.code, errors=e.errors)
            except Exception as e:
                raise ApiError(str(e), 500)

            text = 'alert received via {} webhook'.format(webhook)
            write_audit_trail.send(current_app._get_current_object(), event='webhook-received', message=text,
                                   user=g.login, customers=g.customers, scopes=g.scopes, resource_id=alert.id,
                                   type='alert', request=request)
            alerts.append(alert)

        if len(alerts) == 1:
            return jsonify(status='ok', id=alerts[0].id, alert=alerts[0].serialize), 201
        else:
            return jsonify(status='ok', ids=[alert.id for alert in alerts]), 201

    else:
        text = 'request received via {} webhook'.format(webhook)
        write_audit_trail.send(current_app._get_current_object(), event='webhook-received', message=text,
                               user=g.login, customers=g.customers, scopes=g.scopes, resource_id=None,
                               type='user-defined', request=request)
        return rv
