
import jwt
import requests
from flask import current_app, jsonify, request
from flask_cors import cross_origin

from alerta.auth.utils import create_token, get_customers

from . import auth


@auth.route('/auth/pingfederate', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def pingfederate():

    access_token_url = current_app.config['PINGFEDERATE_OPENID_ACCESS_TOKEN_URL']

    payload = {
        'client_id': request.json['clientId'],
        'client_secret': current_app.config['OAUTH2_CLIENT_SECRET'],
        'redirect_uri': request.json['redirectUri'],
        'grant_type': 'authorization_code',
        'code': request.json['code'],
        'scope': 'openid email',
    }

    try:
        r = requests.post(access_token_url, data=payload)
    except Exception:
        return jsonify(status='error', message='Failed to call sso API over HTTPS')
    access_token = r.json()
    encoded = access_token['access_token']

    keyfile = open(current_app.config['PINGFEDERATE_PUBKEY_LOCATION'], 'r')
    keystring = keyfile.read()

    decoded = jwt.decode(encoded, keystring, algorithms=current_app.config['PINGFEDERATE_TOKEN_ALGORITHM'])

    login = decoded[current_app.config['PINGFEDERATE_OPENID_PAYLOAD_USERNAME']]
    email = decoded[current_app.config['PINGFEDERATE_OPENID_PAYLOAD_EMAIL']]
    customers = get_customers(login, current_app.config['PINGFEDERATE_OPENID_PAYLOAD_GROUP'])

    token = create_token(login, email, email, provider='openid', customers=customers)
    return jsonify(token=token.tokenize)
