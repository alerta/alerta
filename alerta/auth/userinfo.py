
from flask import request, jsonify
from flask_cors import cross_origin

from alerta.exceptions import ApiError
from alerta.auth.utils import permission
from alerta.models.token import Jwt
from . import auth


@auth.route('/userinfo', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission('read:userinfo')
def userinfo():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if token:
        return jsonify(Jwt.parse(token).serialize)
    else:
        raise ApiError('Missing authorization Bearer token', 401)
