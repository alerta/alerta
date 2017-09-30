from flask import jsonify, request, g, current_app
from flask_cors import cross_origin

from alerta.auth.utils import permission
from alerta.exceptions import ApiError
from alerta.models.key import ApiKey
from alerta.models.permission import Permission
from alerta.utils.api import jsonp
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

    if 'admin' in g.scopes or 'admin:keys' in g.scopes:
        key.user = key.user or g.user
        key.customer = key.customer or g.get('customer', None)
    else:
        key.user = g.user
        key.customer = g.get('customer', None)

    if not key.user:
        raise ApiError("Must set 'user' to create API key", 400)

    for want_scope in key.scopes:
        if not Permission.is_in_scope(want_scope, g.scopes):
            raise ApiError("Requested scope '%s' not in existing scopes: %s" % (want_scope, ','.join(g.scopes)), 403)

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
    if not current_app.config['AUTH_REQUIRED']:
        keys = ApiKey.find_all()
    elif 'admin' in g.scopes or 'admin:keys' in g.scopes:
        keys = ApiKey.find_all()
    elif not g.get('user', None):
            raise ApiError("Must define 'user' to list user keys", 400)
    else:
        keys = ApiKey.find_by_user(g.user)

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
    key = ApiKey.get(key)

    if not key:
        raise ApiError("not found", 404)

    if key.delete():
        return jsonify(status="ok")
    else:
        raise ApiError("failed to delete API key", 500)
