
from flask import current_app, g, jsonify, request
from flask_cors import cross_origin

from alerta.auth.decorators import permission
from alerta.exceptions import ApiError
from alerta.models.enums import Scope
from alerta.models.permission import Permission
from alerta.utils.audit import admin_audit_trail
from alerta.utils.response import jsonp

from . import api


@api.route('/perm', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission(Scope.admin_perms)
@jsonp
def create_perm():
    try:
        perm = Permission.parse(request.json)
    except ValueError as e:
        raise ApiError(str(e), 400)

    if perm.match in ['admin', 'user']:
        raise ApiError('{} role already exists'.format(perm.match), 409)

    for want_scope in perm.scopes:
        if not Permission.is_in_scope(want_scope, have_scopes=g.scopes):
            raise ApiError("Requested scope '{}' not in existing scopes: {}".format(
                want_scope, ','.join(g.scopes)), 403)

    try:
        perm = perm.create()
    except Exception as e:
        raise ApiError(str(e), 500)

    admin_audit_trail.send(current_app._get_current_object(), event='permission-created', message='', user=g.user,
                           customers=g.customers, scopes=g.scopes, resource_id=perm.id, type='permission', request=request)

    if perm:
        return jsonify(status='ok', id=perm.id, permission=perm.serialize), 201
    else:
        raise ApiError('create API key failed', 500)


@api.route('/perms', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_perms)
@jsonp
def list_perms():
    perms = Permission.find_all()

    # add system-defined roles 'admin' and 'user'
    admin_perm = Permission(
        match='admin',
        scopes=[Scope.admin]
    )
    perms.append(admin_perm)

    user_perm = Permission(
        match='user',
        scopes=current_app.config['USER_DEFAULT_SCOPES']
    )
    perms.append(user_perm)

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
@permission(Scope.admin_perms)
@jsonp
def delete_perm(perm_id):
    perm = Permission.find_by_id(perm_id)

    if not perm:
        raise ApiError('not found', 404)

    admin_audit_trail.send(current_app._get_current_object(), event='permission-deleted', message='', user=g.user,
                           customers=g.customers, scopes=g.scopes, resource_id=perm.id, type='permission', request=request)

    if perm.delete():
        return jsonify(status='ok')
    else:
        raise ApiError('failed to delete permission', 500)


@api.route('/scopes', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_perms)
@jsonp
def list_scopes():
    scopes = list(Scope)

    return jsonify(
        status='ok',
        scopes=scopes,
        total=len(scopes)
    )
