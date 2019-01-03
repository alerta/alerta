from flask import current_app, g, jsonify, request
from flask_cors import cross_origin

from alerta.app import qb
from alerta.auth.decorators import permission
from alerta.auth.utils import not_authorized
from alerta.exceptions import ApiError
from alerta.models.enums import Scope
from alerta.models.user import User
from alerta.utils.audit import admin_audit_trail, write_audit_trail
from alerta.utils.response import jsonp

from . import api


@api.route('/user', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission(Scope.admin_users)
@jsonp
def create_user():
    try:
        user = User.parse(request.json)
    except Exception as e:
        raise ApiError(str(e), 400)

    # check allowed domain
    if not_authorized('ALLOWED_EMAIL_DOMAINS', groups=[user.domain]):
        raise ApiError('unauthorized domain', 403)

    if User.find_by_email(email=user.email):
        raise ApiError('username already exists', 409)

    try:
        user = user.create()
    except Exception as e:
        ApiError(str(e), 500)

    # if email verification is enforced, send confirmation email
    if current_app.config['EMAIL_VERIFICATION'] and not user.email_verified:
        user.send_confirmation()

    admin_audit_trail.send(current_app._get_current_object(), event='user-created', message='', user=g.user,
                           customers=g.customers, scopes=g.scopes, resource_id=user.id, type='user', request=request)

    if user:
        return jsonify(status='ok', id=user.id, user=user.serialize), 201
    else:
        raise ApiError('create user failed', 500)


@api.route('/user/<user_id>', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.admin_users)
@jsonp
def get_user(user_id):
    user = User.find_by_id(user_id)

    if user:
        return jsonify(status='ok', total=1, user=user.serialize)
    else:
        raise ApiError('not found', 404)


@api.route('/users', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.admin_users)
@jsonp
def search_users():
    query = qb.from_params(request.args)
    users = User.find_all(query)

    # add admins defined in server config
    if 'admin' in request.args.getlist('roles'):
        for admin in set(current_app.config['ADMIN_USERS']):
            user = User.find_by_email(admin)
            if user:
                users.append(user)

    # remove admins whose default role is 'user'
    if 'admin' not in request.args.getlist('roles'):
        users = [u for u in users if 'admin' not in u.roles]

    if users:
        return jsonify(
            status='ok',
            users=[user.serialize for user in users],
            domains=current_app.config['ALLOWED_EMAIL_DOMAINS'],
            total=len(users)
        )
    else:
        return jsonify(
            status='ok',
            message='not found',
            users=[],
            domains=current_app.config['ALLOWED_EMAIL_DOMAINS'],
            total=0
        )


@api.route('/user/<user_id>', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission(Scope.admin_users)
@jsonp
def update_user(user_id):
    if not request.json:
        raise ApiError('nothing to change', 400)

    user = User.find_by_id(user_id)

    if not user:
        raise ApiError('not found', 404)

    if 'email' in request.json:
        user_by_email = User.find_by_email(request.json['email'])
        if user_by_email and user_by_email.id != user.id:
            raise ApiError('user with email already exists', 409)

    admin_audit_trail.send(current_app._get_current_object(), event='user-updated', message='', user=g.user,
                           customers=g.customers, scopes=g.scopes, resource_id=user.id, type='user', request=request)

    if user.update(**request.json):
        return jsonify(status='ok')
    else:
        raise ApiError('failed to update user', 500)


@api.route('/user/me', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission(Scope.write_users)
@jsonp
def update_me():
    if not request.json:
        raise ApiError('nothing to change', 400)

    if 'roles' in request.json:
        raise ApiError('not allowed to update roles', 400)
    if 'email_verified' in request.json:
        raise ApiError('not allowed to set email verified', 400)

    user = User.find_by_email(g.user)

    if not user:
        raise ApiError('not found', 404)

    if 'email' in request.json:
        user_by_email = User.find_by_email(request.json['email'])
        if user_by_email and user_by_email.id != user.id:
            raise ApiError('user with email already exists', 409)

    write_audit_trail.send(current_app._get_current_object(), event='user-me-updated', message='', user=g.user,
                           customers=g.customers, scopes=g.scopes, resource_id=user.id, type='user', request=request)

    if user.update(**request.json):
        return jsonify(status='ok')
    else:
        raise ApiError('failed to update user', 500)


@api.route('/user/<user_id>/attributes', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission(Scope.admin_users)
@jsonp
def update_user_attributes(user_id):
    if not request.json.get('attributes', None):
        raise ApiError("must supply 'attributes' as json data", 400)

    user = User.find_by_id(user_id)

    if not user:
        raise ApiError('not found', 404)

    admin_audit_trail.send(current_app._get_current_object(), event='user-attributes-updated', message='', user=g.user,
                           customers=g.customers, scopes=g.scopes, resource_id=user.id, type='user', request=request)

    if user.update_attributes(request.json['attributes']):
        return jsonify(status='ok')
    else:
        raise ApiError('failed to update attributes', 500)


@api.route('/user/me/attributes', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission(Scope.write_users)
@jsonp
def update_me_attributes():
    if not request.json.get('attributes', None):
        raise ApiError("must supply 'attributes' as json data", 400)

    user = User.find_by_email(g.user)

    if not user:
        raise ApiError('not found', 404)

    write_audit_trail.send(current_app._get_current_object(), event='user-me-attributes-updated', message='', user=g.user,
                           customers=g.customers, scopes=g.scopes, resource_id=user.id, type='user', request=request)

    if user.update_attributes(request.json['attributes']):
        return jsonify(status='ok')
    else:
        raise ApiError('failed to update attributes', 500)


@api.route('/user/<user_id>', methods=['OPTIONS', 'DELETE'])
@cross_origin()
@permission(Scope.admin_users)
@jsonp
def delete_user(user_id):
    user = User.find_by_id(user_id)

    if not user:
        raise ApiError('not found', 404)

    admin_audit_trail.send(current_app._get_current_object(), event='user-deleted', message='', user=g.user,
                           customers=g.customers, scopes=g.scopes, resource_id=user.id, type='user', request=request)

    if user.delete():
        return jsonify(status='ok')
    else:
        raise ApiError('failed to delete user', 500)
