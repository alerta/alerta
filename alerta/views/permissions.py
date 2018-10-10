
from flask import g, jsonify, request
from flask_cors import cross_origin

from alerta.auth.decorators import permission
from alerta.exceptions import ApiError
from alerta.models.permission import Permission
from alerta.utils.response import jsonp

from . import api


@api.route('/perm', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission('admin:perms')
@jsonp
def create_perm():
    try:
        perm = Permission.parse(request.json)
    except ValueError as e:
        raise ApiError(str(e), 400)

    for want_scope in perm.scopes:
        if not Permission.is_in_scope(want_scope, g.scopes):
            raise ApiError("Requested scope '{}' not in existing scopes: {}".format(
                want_scope, ','.join(g.scopes)), 403)

    try:
        perm = perm.create()
    except Exception as e:
        raise ApiError(str(e), 500)

    if perm:
        return jsonify(status='ok', id=perm.id, permission=perm.serialize), 201
    else:
        raise ApiError('create API key failed', 500)


@api.route('/perms', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission('read:perms')
@jsonp
def list_perms():
    perms = Permission.find_all()

    if perms:
        return jsonify(
            status='ok',
            permissions=[perm.serialize for perm in perms],
            total=len(perms)
        )
    else:
        return jsonify(
            status='ok',
            message='not found',
            permissions=[],
            total=0
        )


@api.route('/perm/<perm_id>', methods=['OPTIONS', 'DELETE'])
@cross_origin()
@permission('admin:perms')
@jsonp
def delete_perm(perm_id):
    perm = Permission.find_by_id(perm_id)

    if not perm:
        raise ApiError('not found', 404)

    if perm.delete():
        return jsonify(status='ok')
    else:
        raise ApiError('failed to delete permission', 500)
