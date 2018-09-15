
from uuid import uuid4

from flask import current_app, g, jsonify, request
from flask_cors import cross_origin

from alerta.app import qb
from alerta.auth.decorators import permission
from alerta.auth.utils import (create_token, get_customers, not_authorized,
                               send_confirmation)
from alerta.exceptions import ApiError
from alerta.models.user import User
from alerta.utils.api import jsonp

from . import api


@api.route('/user', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission('admin:users')
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

    # if email verification is enforced, deny login and send email
    if current_app.config['EMAIL_VERIFICATION'] and not user.email_verified:
        hash = str(uuid4())
        send_confirmation(user, hash)
        user.set_email_hash(hash)
        raise ApiError('email not verified', 401)

    # check user is active
    if user.status != 'active':
        raise ApiError('user not active', 403)

    # assign customers & update last login time
    customers = get_customers(user.email, groups=[user.domain])
    user.update_last_login()

    # generate token
    token = create_token(user.id, user.name, user.email, provider='basic', customers=customers,
                         roles=user.roles, email=user.email, email_verified=user.email_verified)
    return jsonify(token=token.tokenize)


@api.route('/user/<user_id>', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission('admin:users')
@jsonp
def update_user(user_id):
    if not request.json:
        raise ApiError('nothing to change', 400)

    user = User.find_by_id(user_id)

    if not user:
        raise ApiError('not found', 404)

    if 'email' in request.json and User.find_by_email(request.json['email']):
        raise ApiError('user with email already exists', 409)

    if user.update(**request.json):
        return jsonify(status='ok')
    else:
        raise ApiError('failed to update user', 500)


@api.route('/user/me', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission('write:users')
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

    if 'email' in request.json and User.find_by_email(request.json['email']):
        raise ApiError('user with email already exists', 409)

    if user.update(**request.json):
        return jsonify(status='ok')
    else:
        raise ApiError('failed to update user', 500)


@api.route('/user/<user_id>/attributes', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission('admin:users')
@jsonp
def update_user_attributes(user_id):
    if not request.json.get('attributes', None):
        raise ApiError("must supply 'attributes' as json data", 400)

    user = User.find_by_id(user_id)

    if not user:
        raise ApiError('not found', 404)

    if user.update_attributes(request.json['attributes']):
        return jsonify(status='ok')
    else:
        raise ApiError('failed to update attributes', 500)


@api.route('/user/me/attributes', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission('write:users')
@jsonp
def update_me_attributes():
    if not request.json.get('attributes', None):
        raise ApiError("must supply 'attributes' as json data", 400)

    user = User.find_by_email(g.user)

    if not user:
        raise ApiError('not found', 404)

    if user.update_attributes(request.json['attributes']):
        return jsonify(status='ok')
    else:
        raise ApiError('failed to update attributes', 500)


@api.route('/users', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission('admin:users')
@jsonp
def search_users():
    query = qb.from_params(request.args)
    users = User.find_all(query)

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


@api.route('/user/<user_id>', methods=['OPTIONS', 'DELETE'])
@cross_origin()
@permission('admin:users')
@jsonp
def delete_user(user_id):
    user = User.find_by_id(user_id)

    if not user:
        raise ApiError('not found', 404)

    if user.delete():
        return jsonify(status='ok')
    else:
        raise ApiError('failed to delete user', 500)
