
from flask import g, jsonify, request
from flask_cors import cross_origin

from alerta.app import qb
from alerta.auth.decorators import permission
from alerta.exceptions import ApiError
from alerta.models.blackout import Blackout
from alerta.utils.api import assign_customer
from alerta.utils.response import absolute_url, jsonp

from . import api


@api.route('/blackout', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission('write:blackouts')
@jsonp
def create_blackout():
    try:
        blackout = Blackout.parse(request.json)
    except Exception as e:
        raise ApiError(str(e), 400)

    if 'admin' in g.scopes or 'admin:blackouts' in g.scopes:
        blackout.user = blackout.user or g.user
    else:
        blackout.user = g.user

    blackout.customer = assign_customer(wanted=blackout.customer, permission='admin:blackouts')

    try:
        blackout = blackout.create()
    except Exception as e:
        raise ApiError(str(e), 500)

    if blackout:
        return jsonify(status='ok', id=blackout.id, blackout=blackout.serialize), 201, {'Location': absolute_url('/blackout/' + blackout.id)}
    else:
        raise ApiError('insert blackout failed', 500)


@api.route('/blackouts', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission('read:blackouts')
@jsonp
def list_blackouts():
    query = qb.from_params(request.args)
    blackouts = Blackout.find_all(query)

    if blackouts:
        return jsonify(
            status='ok',
            blackouts=[blackout.serialize for blackout in blackouts],
            total=len(blackouts)
        )
    else:
        return jsonify(
            status='ok',
            message='not found',
            blackouts=[],
            total=0
        )


@api.route('/blackout/<blackout_id>', methods=['OPTIONS', 'DELETE'])
@cross_origin()
@permission('write:blackouts')
@jsonp
def delete_blackout(blackout_id):
    customer = g.get('customer', None)
    blackout = Blackout.find_by_id(blackout_id, customer)

    if not blackout:
        raise ApiError('not found', 404)

    if blackout.delete():
        return jsonify(status='ok')
    else:
        raise ApiError('failed to delete blackout', 500)
