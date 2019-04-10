
from flask import current_app, g, jsonify, request
from flask_cors import cross_origin

from alerta.app import qb
from alerta.auth.decorators import permission
from alerta.exceptions import ApiError
from alerta.models.blackout import Blackout
from alerta.models.enums import Scope
from alerta.utils.api import assign_customer
from alerta.utils.audit import write_audit_trail
from alerta.utils.response import absolute_url, jsonp

from . import api


@api.route('/blackout', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission(Scope.write_blackouts)
@jsonp
def create_blackout():
    try:
        blackout = Blackout.parse(request.json)
    except Exception as e:
        raise ApiError(str(e), 400)

    if Scope.admin in g.scopes or Scope.admin_blackouts in g.scopes:
        blackout.user = blackout.user or g.login
    else:
        blackout.user = g.login

    blackout.customer = assign_customer(wanted=blackout.customer, permission=Scope.admin_blackouts)

    try:
        blackout = blackout.create()
    except Exception as e:
        raise ApiError(str(e), 500)

    write_audit_trail.send(current_app._get_current_object(), event='blackout-created', message='', user=g.login,
                           customers=g.customers, scopes=g.scopes, resource_id=blackout.id, type='blackout', request=request)

    if blackout:
        return jsonify(status='ok', id=blackout.id, blackout=blackout.serialize), 201, {'Location': absolute_url('/blackout/' + blackout.id)}
    else:
        raise ApiError('insert blackout failed', 500)


@api.route('/blackout/<blackout_id>', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_blackouts)
@jsonp
def get_blackout(blackout_id):
    blackout = Blackout.find_by_id(blackout_id)

    if blackout:
        return jsonify(status='ok', total=1, blackout=blackout.serialize)
    else:
        raise ApiError('not found', 404)


@api.route('/blackouts', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_blackouts)
@jsonp
def list_blackouts():
    query = qb.from_params(request.args, customers=g.customers)
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


@api.route('/blackout/<blackout_id>', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission(Scope.write_blackouts)
@jsonp
def update_blackout(blackout_id):
    if not request.json:
        raise ApiError('nothing to change', 400)

    if not current_app.config['AUTH_REQUIRED']:
        blackout = Blackout.find_by_id(blackout_id)
    elif Scope.admin in g.scopes or Scope.admin_blackouts in g.scopes:
        blackout = Blackout.find_by_id(blackout_id)
    else:
        blackout = Blackout.find_by_id(blackout_id, g.customers)

    if not blackout:
        raise ApiError('not found', 404)

    update = request.json
    update['user'] = g.login
    update['customer'] = assign_customer(wanted=update.get('customer'), permission=Scope.admin_blackouts)

    write_audit_trail.send(current_app._get_current_object(), event='blackout-updated', message='', user=g.login,
                           customers=g.customers, scopes=g.scopes, resource_id=blackout.id, type='blackout',
                           request=request)

    if blackout.update(**update):
        return jsonify(status='ok')
    else:
        raise ApiError('failed to update blackout', 500)


@api.route('/blackout/<blackout_id>', methods=['OPTIONS', 'DELETE'])
@cross_origin()
@permission(Scope.write_blackouts)
@jsonp
def delete_blackout(blackout_id):
    customer = g.get('customer', None)
    blackout = Blackout.find_by_id(blackout_id, customer)

    if not blackout:
        raise ApiError('not found', 404)

    write_audit_trail.send(current_app._get_current_object(), event='blackout-deleted', message='', user=g.login,
                           customers=g.customers, scopes=g.scopes, resource_id=blackout.id, type='blackout', request=request)

    if blackout.delete():
        return jsonify(status='ok')
    else:
        raise ApiError('failed to delete blackout', 500)
