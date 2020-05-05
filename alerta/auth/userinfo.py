import re

from flask import jsonify, request
from flask_cors import cross_origin

from alerta.auth.decorators import permission
from alerta.exceptions import ApiError
from alerta.models.enums import Scope
from alerta.models.token import Jwt

from . import auth


@auth.route('/userinfo', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_userinfo)
def userinfo():
    auth_header = request.headers.get('Authorization', '')
    m = re.match(r'Bearer (\S+)', auth_header)
    token = m.group(1) if m else None

    if token:
        return jsonify(Jwt.parse(token).serialize)
    else:
        raise ApiError('Missing authorization Bearer token', 401)
