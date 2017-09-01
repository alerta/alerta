
from flask import request, jsonify
from flask_cors import cross_origin

from alerta.app.auth.utils import permission
from alerta.app.models.token import Jwt

from . import auth


@auth.route('/userinfo', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission('read:userinfo')
def userinfo():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    return jsonify(Jwt.parse(token).serialize)
