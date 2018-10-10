
from flask import g, jsonify, request
from flask_cors import cross_origin

from alerta.app import qb
from alerta.auth.decorators import permission
from alerta.exceptions import ApiError
from alerta.models.heartbeat import Heartbeat
from alerta.utils.api import assign_customer
from alerta.utils.response import jsonp

from . import api


@api.route('/heartbeat', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission('write:heartbeats')
@jsonp
def create_heartbeat():
    try:
        heartbeat = Heartbeat.parse(request.json)
    except ValueError as e:
        raise ApiError(str(e), 400)

    heartbeat.customer = assign_customer(wanted=heartbeat.customer, permission='admin:heartbeats')

    try:
        heartbeat = heartbeat.create()
    except Exception as e:
        raise ApiError(str(e), 500)

    if heartbeat:
        return jsonify(status='ok', id=heartbeat.id, heartbeat=heartbeat.serialize), 201
    else:
        raise ApiError('insert or update of received heartbeat failed', 500)


@api.route('/heartbeat/<heartbeat_id>', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission('read:heartbeats')
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
@permission('read:heartbeats')
@jsonp
def list_heartbeats():
    query = qb.from_params(request.args)
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
@permission('write:heartbeats')
@jsonp
def delete_heartbeat(heartbeat_id):
    customer = g.get('customer', None)
    heartbeat = Heartbeat.find_by_id(heartbeat_id, customer)

    if not heartbeat:
        raise ApiError('not found', 404)

    if heartbeat.delete():
        return jsonify(status='ok')
    else:
        raise ApiError('failed to delete heartbeat', 500)
