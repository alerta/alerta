
from flask import jsonify, request, current_app
from flask_cors import cross_origin

from alerta.app import qb
from alerta.app.auth.utils import permission
from alerta.app.exceptions import ApiError
from alerta.app.models.user import User
from alerta.app.utils.api import jsonp
from . import api


# NOTE: "user create" method is basic auth "sign up" method


@api.route('/user/<user_id>', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission('admin:users')
@jsonp
def update_user(user_id):
    if not request.json:
        raise ApiError("nothing to change", 400)

    user = User.get(user_id)

    if not user:
        raise ApiError("not found", 404)

    if user.update(**request.json):
        return jsonify(status="ok")
    else:
        raise ApiError("failed to update user", 500)


@api.route('/users', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission('admin:users')
@jsonp
def list_users():
    query = qb.from_params(request.args)
    users = User.find_all(query)

    if users:
        return jsonify(
            status="ok",
            users=[user.serialize for user in users],
            domains=current_app.config['ALLOWED_EMAIL_DOMAINS'],
            orgs=current_app.config['ALLOWED_GITHUB_ORGS'],
            groups=current_app.config['ALLOWED_GITLAB_GROUPS'],
            roles=current_app.config['ALLOWED_KEYCLOAK_ROLES'],
            total=len(users)
        )
    else:
        return jsonify(
            status="ok",
            message="not found",
            users=[],
            domains=current_app.config['ALLOWED_EMAIL_DOMAINS'],
            orgs=current_app.config['ALLOWED_GITHUB_ORGS'],
            groups=current_app.config['ALLOWED_GITLAB_GROUPS'],
            roles=current_app.config['ALLOWED_KEYCLOAK_ROLES'],
            total=0
        )


@api.route('/user/<user_id>', methods=['OPTIONS', 'DELETE'])
@cross_origin()
@permission('write:users')
@jsonp
def delete_user(user_id):
    user = User.get(user_id)

    if not user:
        raise ApiError("not found", 404)

    if user.delete():
        return jsonify(status="ok")
    else:
        raise ApiError("failed to delete user", 500)
