
import jwt
import requests
from flask import current_app, jsonify, request
from flask_cors import cross_origin

from alerta.auth.utils import create_token, get_customers
from alerta.models.permission import Permission
from alerta.utils.audit import auth_audit_trail

from . import auth


@auth.route('/auth/pingfederate', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def pingfederate():

    access_token_url = current_app.config['PINGFEDERATE_OPENID_ACCESS_TOKEN_URL']

    data = {
        'grant_type': 'authorization_code',
        'code': request.json['code'],
        'redirect_uri': request.json['redirectUri'],
        'client_id': request.json['clientId'],
        'client_secret': current_app.config['OAUTH2_CLIENT_SECRET']
    }

    r = requests.post(access_token_url, data)
    token = r.json()

    keyfile = open(current_app.config['PINGFEDERATE_PUBKEY_LOCATION'], 'r')
    keystring = keyfile.read()

    access_token = jwt.decode(
        token['access_token'],
        keystring,
        algorithms=current_app.config['PINGFEDERATE_TOKEN_ALGORITHM']
    )

    login = access_token[current_app.config['PINGFEDERATE_OPENID_PAYLOAD_USERNAME']]
    email = access_token[current_app.config['PINGFEDERATE_OPENID_PAYLOAD_EMAIL']]
    groups = access_token[current_app.config['PINGFEDERATE_OPENID_PAYLOAD_GROUP']]

    customers = get_customers(login, groups=groups)
    scopes = Permission.lookup(login, roles=groups)

    auth_audit_trail.send(current_app._get_current_object(), event='pingfederate-login', message='user login via PingFederate',
                          user=email, customers=customers, scopes=scopes, resource_id=login, type='user', request=request)

    token = create_token(user_id=login, name=email, login=email, provider='openid', customers=customers, scopes=scopes,
                         email=email, email_verified=True, groups=groups)
    return jsonify(token=token.tokenize)
