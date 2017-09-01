
from flask import jsonify, request, g
from flask_cors import cross_origin

from alerta.app.auth.utils import permission
from alerta.app.models.key import ApiKey
from alerta.app.models.permission import Permission
from alerta.app.utils.api import jsonp
from alerta.app.exceptions import ApiError

from . import api


@api.route('/key', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission('write:keys')
@jsonp
def create_key():
    try:
        key = ApiKey.parse(request.json)
    except ValueError as e:
        raise ApiError(str(e), 400)
    print(key)

    # if 'admin' not in g.scopes and 'admin:keys' not in g.scopes:
    #     key.user = g.user
    #     key.customer = g.get('customer', None)

    # if not key.user:
    #     raise ApiError("Must set 'user' to create API key", 400)
    #
    # for want_scope in key.scopes:
    #     if not Permission.is_in_scope(want_scope, g.scopes):
    #         raise ApiError("Requested scope '%s' not in existing scopes: %s" % (want_scope, ','.join(g.scopes)), 403)

    try:
        key = key.create()
    except Exception as e:
        raise ApiError(str(e), 500)

    if key:
        return jsonify(status="ok", key=key.key, data=key.serialize), 201
    else:
        raise ApiError("create API key failed", 500)


@api.route('/keys', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission('read:keys')
@jsonp
def list_keys():
    if 'admin' in g.scopes or 'admin:keys' in g.scopes:
        keys = ApiKey.find_all()
    else:
        user = g.get('user')
        keys = ApiKey.find_by_user(user)

    if keys:
        return jsonify(
            status="ok",
            keys=[key.serialize for key in keys],
            total=len(keys)
        )
    else:
        return jsonify(
            status="ok",
            message="not found",
            keys=[],
            total=0
        )


@api.route('/key/<path:key>', methods=['OPTIONS', 'DELETE'])
@cross_origin()
@permission('admin:keys')
@jsonp
def delete_key(key):
    customer = g.get('customer', None)
    key = ApiKey.get(key, customer)

    if not key:
        raise ApiError("not found", 404)

    if key.delete():
        return jsonify(status="ok")
    else:
        raise ApiError("failed to delete API key", 500)
