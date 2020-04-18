from flask import current_app, g, jsonify, request
from flask_cors import cross_origin

from alerta.app import qb
from alerta.auth.decorators import permission
from alerta.exceptions import ApiError
from alerta.models.enums import Scope
from alerta.models.group import Group, GroupUsers
from alerta.models.user import User
from alerta.utils.audit import admin_audit_trail
from alerta.utils.response import jsonp

from . import api


@api.route('/group', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission(Scope.admin_groups)
@jsonp
def create_group():
    try:
        group = Group.parse(request.json)
    except ValueError as e:
        raise ApiError(str(e), 400)

    try:
        group = group.create()
    except Exception as e:
        raise ApiError(str(e), 500)

    admin_audit_trail.send(current_app._get_current_object(), event='group-created', message='', user=g.login,
                           customers=g.customers, scopes=g.scopes, resource_id=group.id, type='group', request=request)

    if group:
        return jsonify(status='ok', id=group.id, group=group.serialize), 201
    else:
        raise ApiError('create user group failed', 500)


@api.route('/group/<group_id>', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_groups)
@jsonp
def get_group(group_id):
    group = Group.find_by_id(group_id)

    if group:
        return jsonify(status='ok', total=1, group=group.serialize)
    else:
        raise ApiError('not found', 404)


@api.route('/group/<group_id>/users', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_groups)
@jsonp
def get_group_users(group_id):
    if not Group.find_by_id(group_id):
        raise ApiError('not found', 404)

    group_users = GroupUsers.find_by_id(group_id)

    if group_users:
        return jsonify(
            status='ok',
            users=[user.serialize for user in group_users],
            total=len(group_users)
        )
    else:
        return jsonify(
            status='ok',
            users=[],
            total=0
        )


@api.route('/groups', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_groups)
@jsonp
def list_groups():
    query = qb.from_params(request.args)
    groups = Group.find_all(query)

    if groups:
        return jsonify(
            status='ok',
            groups=[group.serialize for group in groups],
            total=len(groups)
        )
    else:
        return jsonify(
            status='ok',
            message='not found',
            groups=[],
            total=0
        )


@api.route('/group/<group_id>', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission(Scope.admin_groups)
@jsonp
def update_group(group_id):
    if not request.json:
        raise ApiError('nothing to change', 400)

    group = Group.find_by_id(group_id)

    if not group:
        raise ApiError('not found', 404)

    admin_audit_trail.send(current_app._get_current_object(), event='group-updated', message='', user=g.login,
                           customers=g.customers, scopes=g.scopes, resource_id=group.id, type='group', request=request)

    updated = group.update(**request.json)
    if updated:
        return jsonify(status='ok', group=updated.serialize)
    else:
        raise ApiError('failed to update user group', 500)


@api.route('/group/<group_id>/user/<user_id>', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission(Scope.admin_groups)
@jsonp
def add_user_to_group(group_id, user_id):
    group = Group.find_by_id(group_id)
    if not group:
        raise ApiError('not found', 404)

    user = User.find_by_id(user_id)
    if not user:
        raise ApiError('invalid user', 400)

    admin_audit_trail.send(current_app._get_current_object(), event='user-attributes-updated', message='', user=g.login,
                           customers=g.customers, scopes=g.scopes, resource_id=user.id, type='user', request=request)

    if group.add_user(user_id):
        return jsonify(status='ok')
    else:
        raise ApiError('failed to add user to group', 500)


@api.route('/group/<group_id>/user/<user_id>', methods=['OPTIONS', 'DELETE'])
@cross_origin()
@permission(Scope.admin_groups)
@jsonp
def remove_user_from_group(group_id, user_id):
    group = Group.find_by_id(group_id)
    if not group:
        raise ApiError('not found', 404)

    user = User.find_by_id(user_id)
    if not user:
        raise ApiError('invalid user', 400)

    admin_audit_trail.send(current_app._get_current_object(), event='user-attributes-updated', message='', user=g.login,
                           customers=g.customers, scopes=g.scopes, resource_id=user.id, type='user', request=request)

    if group.remove_user(user_id):
        return jsonify(status='ok')
    else:
        raise ApiError('failed to remove user from group', 500)


@api.route('/group/<group_id>', methods=['OPTIONS', 'DELETE'])
@cross_origin()
@permission(Scope.admin_groups)
@jsonp
def delete_group(group_id):
    group = Group.find_by_id(group_id)

    if not group:
        raise ApiError('not found', 404)

    admin_audit_trail.send(current_app._get_current_object(), event='group-deleted', message='', user=g.login,
                           customers=g.customers, scopes=g.scopes, resource_id=group.id, type='group', request=request)

    if group.delete():
        return jsonify(status='ok')
    else:
        raise ApiError('failed to delete user group', 500)
