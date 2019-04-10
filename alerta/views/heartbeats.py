
from flask import current_app, g, jsonify, request
from flask_cors import cross_origin

from alerta.app import qb
from alerta.auth.decorators import permission
from alerta.exceptions import ApiError
from alerta.models.enums import Scope
from alerta.models.heartbeat import Heartbeat
from alerta.utils.api import assign_customer
from alerta.utils.audit import write_audit_trail
from alerta.utils.response import jsonp

from . import api


@api.route('/heartbeat', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission(Scope.write_heartbeats)
@jsonp
def create_heartbeat():
    try:
        heartbeat = Heartbeat.parse(request.json)
    except ValueError as e:
        raise ApiError(str(e), 400)

    heartbeat.customer = assign_customer(wanted=heartbeat.customer, permission=Scope.admin_heartbeats)

    try:
        heartbeat = heartbeat.create()
    except Exception as e:
        raise ApiError(str(e), 500)

    write_audit_trail.send(current_app._get_current_object(), event='heartbeat-created', message='', user=g.login,
                           customers=g.customers, scopes=g.scopes, resource_id=heartbeat.id, type='heartbeat', request=request)

    if heartbeat:
        return jsonify(status='ok', id=heartbeat.id, heartbeat=heartbeat.serialize), 201
    else:
        raise ApiError('insert or update of received heartbeat failed', 500)


@api.route('/heartbeat/<heartbeat_id>', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_heartbeats)
@jsonp
def get_heartbeat(heartbeat_id):
    customer = g.get('customer', None)
    heartbeat = Heartbeat.find_by_id(heartbeat_id, customer)

    if heartbeat:
        return jsonify(status='ok', total=1, heartbeat=heartbeat.serialize)
    else:
        raise ApiError('not found', 404)


@api.route('/heartbeats', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_heartbeats)
@jsonp
def list_heartbeats():
    query = qb.from_params(request.args, customers=g.customers)
    heartbeats = Heartbeat.find_all(query)

    if heartbeats:
        return jsonify(
            status='ok',
            heartbeats=[heartbeat.serialize for heartbeat in heartbeats],
            total=len(heartbeats)
        )
    else:
        return jsonify(
            status='ok',
            message='not found',
            heartbeats=[],
            total=0
        )


@api.route('/heartbeat/<heartbeat_id>', methods=['OPTIONS', 'DELETE'])
@cross_origin()
@permission(Scope.write_heartbeats)
@jsonp
def delete_heartbeat(heartbeat_id):
    customer = g.get('customer', None)
    heartbeat = Heartbeat.find_by_id(heartbeat_id, customer)

    if not heartbeat:
        raise ApiError('not found', 404)

    write_audit_trail.send(current_app._get_current_object(), event='heartbeat-deleted', message='', user=g.login,
                           customers=g.customers, scopes=g.scopes, resource_id=heartbeat.id, type='heartbeat', request=request)

    if heartbeat.delete():
        return jsonify(status='ok')
    else:
        raise ApiError('failed to delete heartbeat', 500)
