from flask import current_app, g, jsonify, request
from flask_cors import cross_origin

from alerta.app import qb
from alerta.auth.decorators import permission
from alerta.exceptions import ApiError
from alerta.models.enums import ADMIN_SCOPES, Scope
from alerta.models.permission import Permission
from alerta.utils.audit import admin_audit_trail
from alerta.utils.paging import Page
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

    if perm.match in [
        current_app.config['DEFAULT_ADMIN_ROLE'],
        current_app.config['DEFAULT_USER_ROLE'],
        current_app.config['DEFAULT_GUEST_ROLE']
    ]:
        raise ApiError('{} role already exists'.format(perm.match), 409)

    for want_scope in perm.scopes:
        if not Permission.is_in_scope(want_scope, have_scopes=g.scopes):
            raise ApiError("Requested scope '{}' not in existing scopes: {}".format(
                want_scope, ','.join(g.scopes)), 403)

    try:
        perm = perm.create()
    except Exception as e:
        raise ApiError(str(e), 500)

    admin_audit_trail.send(current_app._get_current_object(), event='permission-created', message='', user=g.login,
                           customers=g.customers, scopes=g.scopes, resource_id=perm.id, type='permission', request=request)

    if perm:
        return jsonify(status='ok', id=perm.id, permission=perm.serialize), 201
    else:
        raise ApiError('create permission failed', 500)


@api.route('/perm/<perm_id>', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_perms)
@jsonp
def get_perm(perm_id):
    perm = Permission.find_by_id(perm_id)

    if perm:
        return jsonify(status='ok', total=1, permission=perm.serialize)
    else:
        raise ApiError('not found', 404)


@api.route('/perms', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_perms)
@jsonp
def list_perms():

    query = qb.perms.from_params(request.args)
    total = Permission.count(query)
    perms: list[Permission] = []

    admin_perm = Permission(
        match=current_app.config['DEFAULT_ADMIN_ROLE'],
        scopes=ADMIN_SCOPES
    )
    user_perm = Permission(
        match=current_app.config['DEFAULT_USER_ROLE'],
        scopes=current_app.config['USER_DEFAULT_SCOPES']
    )
    guest_perm = Permission(
        match=current_app.config['DEFAULT_GUEST_ROLE'],
        scopes=current_app.config['GUEST_DEFAULT_SCOPES']
    )

    # add system-defined roles 'admin', 'user' and 'guest
    if 'scopes' in request.args:
        want_scopes = request.args.getlist('scopes')
        if set(admin_perm.scopes) & set(want_scopes):
            perms.append(admin_perm)
            total += 1
        if set(user_perm.scopes) & set(want_scopes):
            perms.append(user_perm)
            total += 1
        if set(guest_perm.scopes) & set(want_scopes):
            perms.append(guest_perm)
            total += 1
    else:
        perms.append(admin_perm)
        perms.append(user_perm)
        perms.append(guest_perm)
        total += 3

    paging = Page.from_params(request.args, total)
    perms.extend(Permission.find_all(query, page=paging.page, page_size=paging.page_size))

    if perms:
        return jsonify(
            status='ok',
            page=paging.page,
            pageSize=paging.page_size,
            pages=paging.pages,
            more=paging.has_more,
            permissions=[perm.serialize for perm in perms],
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
            permissions=[],
            total=0
        )


@api.route('/perm/<perm_id>', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission(Scope.admin_perms)
@jsonp
def update_perm(perm_id):
    if not request.json:
        raise ApiError('nothing to change', 400)

    for s in request.json.get('scopes', []):
        if s not in Scope.find_all():
            raise ApiError("'{}' is not a valid Scope".format(s), 400)

    perm = Permission.find_by_id(perm_id)

    if not perm:
        raise ApiError('not found', 404)

    admin_audit_trail.send(current_app._get_current_object(), event='permission-updated', message='', user=g.login,
                           customers=g.customers, scopes=g.scopes, resource_id=perm.id, type='permission', request=request)

    updated = perm.update(**request.json)
    if updated:
        return jsonify(status='ok', permission=updated.serialize)
    else:
        raise ApiError('failed to update permission', 500)


@api.route('/perm/<perm_id>', methods=['OPTIONS', 'DELETE'])
@cross_origin()
@permission(Scope.admin_perms)
@jsonp
def delete_perm(perm_id):
    perm = Permission.find_by_id(perm_id)

    if not perm:
        raise ApiError('not found', 404)

    admin_audit_trail.send(current_app._get_current_object(), event='permission-deleted', message='', user=g.login,
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
    scopes = Scope.find_all()

    return jsonify(
        status='ok',
        scopes=scopes,
        total=len(scopes)
    )
