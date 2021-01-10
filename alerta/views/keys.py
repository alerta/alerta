from flask import current_app, g, jsonify, request
from flask_cors import cross_origin

from alerta.app import qb
from alerta.auth.decorators import permission
from alerta.exceptions import ApiError
from alerta.models.enums import Scope
from alerta.models.key import ApiKey
from alerta.models.permission import Permission
from alerta.utils.api import assign_customer
from alerta.utils.audit import admin_audit_trail, write_audit_trail
from alerta.utils.paging import Page
from alerta.utils.response import jsonp

from . import api


@api.route('/key', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission(Scope.write_keys)
@jsonp
def create_key():
    try:
        key = ApiKey.parse(request.json)
    except ValueError as e:
        raise ApiError(str(e), 400)

    if Scope.admin in g.scopes or Scope.admin_keys in g.scopes:
        key.user = key.user or g.login
    else:
        key.user = g.login

    key.customer = assign_customer(wanted=key.customer, permission=Scope.admin_keys)

    if not key.user:
        raise ApiError("An API key must be associated with a 'user'. Retry with user credentials.", 400)

    for want_scope in key.scopes:
        if not Permission.is_in_scope(want_scope, have_scopes=g.scopes):
            raise ApiError("Requested scope '{}' not in existing scopes: {}".format(
                want_scope, ','.join(g.scopes)), 403)

    try:
        key = key.create()
    except Exception as e:
        raise ApiError(str(e), 500)

    write_audit_trail.send(current_app._get_current_object(), event='apikey-created', message='', user=g.login,
                           customers=g.customers, scopes=g.scopes, resource_id=key.id, type='apikey', request=request)

    if key:
        return jsonify(status='ok', key=key.key, data=key.serialize), 201
    else:
        raise ApiError('create API key failed', 500)


@api.route('/key/<path:key>', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_keys)
@jsonp
def get_key(key):
    if not current_app.config['AUTH_REQUIRED']:
        key = ApiKey.find_by_id(key)
    elif Scope.admin in g.scopes or Scope.admin_keys in g.scopes:
        key = ApiKey.find_by_id(key)
    else:
        user = g.get('login', None)
        key = ApiKey.find_by_id(key, user)

    if key:
        return jsonify(status='ok', total=1, key=key.serialize)
    else:
        raise ApiError('not found', 404)


@api.route('/keys', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_keys)
@jsonp
def list_keys():
    query = qb.keys.from_params(request.args, customers=g.customers)
    total = ApiKey.count(query)
    paging = Page.from_params(request.args, total)
    if not current_app.config['AUTH_REQUIRED']:
        keys = ApiKey.find_all(query, page=paging.page, page_size=paging.page_size)
    elif Scope.admin in g.scopes or Scope.admin_keys in g.scopes:
        keys = ApiKey.find_all(query, page=paging.page, page_size=paging.page_size)
    elif not g.get('login', None):
        raise ApiError("Must define 'user' to list user keys", 400)
    else:
        keys = ApiKey.find_by_user(user=g.login)

    if keys:
        return jsonify(
            status='ok',
            page=paging.page,
            pageSize=paging.page_size,
            pages=paging.pages,
            more=paging.has_more,
            keys=[key.serialize for key in keys],
            total=total
        )
    else:
        return jsonify(
            status='ok',
            page=paging.page,
            pageSize=paging.page_size,
            pages=paging.pages,
            more=paging.has_more,
            message='not found',
            keys=[],
            total=0
        )


@api.route('/key/<path:key>', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission(Scope.write_keys)
@jsonp
def update_key(key):
    if not request.json:
        raise ApiError('nothing to change', 400)

    if not current_app.config['AUTH_REQUIRED']:
        key = ApiKey.find_by_id(key)
    elif Scope.admin in g.scopes or Scope.admin_keys in g.scopes:
        key = ApiKey.find_by_id(key)
    else:
        key = ApiKey.find_by_id(key, user=g.login)

    if not key:
        raise ApiError('not found', 404)

    update = request.json
    update['customer'] = assign_customer(wanted=update.get('customer'), permission=Scope.admin_keys)

    for want_scope in update.get('scopes', []):
        if not Permission.is_in_scope(want_scope, have_scopes=g.scopes):
            raise ApiError("Requested scope '{}' not in existing scopes: {}".format(
                want_scope, ','.join(g.scopes)), 403)

    admin_audit_trail.send(current_app._get_current_object(), event='apikey-updated', message='', user=g.login,
                           customers=g.customers, scopes=g.scopes, resource_id=key.id, type='apikey', request=request)

    updated = key.update(**request.json)
    if updated:
        return jsonify(status='ok', key=updated.serialize)
    else:
        raise ApiError('failed to update API key', 500)


@api.route('/key/<path:key>', methods=['OPTIONS', 'DELETE'])
@cross_origin()
@permission(Scope.admin_keys)
@jsonp
def delete_key(key):
    key = ApiKey.find_by_id(key)

    if not key:
        raise ApiError('not found', 404)

    admin_audit_trail.send(current_app._get_current_object(), event='apikey-deleted', message='', user=g.login,
                           customers=g.customers, scopes=g.scopes, resource_id=key.id, type='apikey', request=request)

    if key.delete():
        return jsonify(status='ok')
    else:
        raise ApiError('failed to delete API key', 500)
