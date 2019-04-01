
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
        'client_id': request.json['clientId'],
        'client_secret': current_app.config['OAUTH2_CLIENT_SECRET'],
        'redirect_uri': request.json['redirectUri'],
        'grant_type': 'authorization_code',
        'code': request.json['code'],
        'scope': 'openid email',
    }

    r = requests.post(access_token_url, data)
    access_token = r.json()
    encoded = access_token['access_token']

    keyfile = open(current_app.config['PINGFEDERATE_PUBKEY_LOCATION'], 'r')
    keystring = keyfile.read()

    decoded = jwt.decode(encoded, keystring, algorithms=current_app.config['PINGFEDERATE_TOKEN_ALGORITHM'])

    login = decoded[current_app.config['PINGFEDERATE_OPENID_PAYLOAD_USERNAME']]
    email = decoded[current_app.config['PINGFEDERATE_OPENID_PAYLOAD_EMAIL']]

    scopes = Permission.lookup(login, roles=[])
    customers = get_customers(login, current_app.config['PINGFEDERATE_OPENID_PAYLOAD_GROUP'])

    auth_audit_trail.send(current_app._get_current_object(), event='pingfederate-login', message='user login via PingFederate',
                          user=email, customers=customers, scopes=scopes,
                          resource_id=login, type='pingfederate', request=request)

    token = create_token(user_id=login, name=email, login=email, provider='openid', customers=customers, scopes=scopes)
    return jsonify(token=token.tokenize)
