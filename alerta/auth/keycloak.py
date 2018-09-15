
import requests
from flask import current_app, jsonify, request
from flask_cors import cross_origin

from alerta.auth.utils import create_token, get_customers, not_authorized
from alerta.exceptions import ApiError

from . import auth


@auth.route('/auth/keycloak', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def keycloak():

    if not current_app.config['KEYCLOAK_URL']:
        return jsonify(status='error', message='Must define KEYCLOAK_URL setting in server configuration.'), 503

    access_token_url = '{}/auth/realms/{}/protocol/openid-connect/token'.format(
        current_app.config['KEYCLOAK_URL'], current_app.config['KEYCLOAK_REALM'])

    payload = {
        'client_id': request.json['clientId'],
        'client_secret': current_app.config['OAUTH2_CLIENT_SECRET'],
        'redirect_uri': request.json['redirectUri'],
        'grant_type': 'authorization_code',
        'code': request.json['code'],
    }

    try:
        r = requests.post(access_token_url, data=payload)
    except Exception:
        return jsonify(status='error', message='Failed to call Keycloak API over HTTPS')
    access_token = r.json()

    headers = {'Authorization': '{} {}'.format(access_token['token_type'], access_token['access_token'])}
    r = requests.get('{}/auth/realms/{}/protocol/openid-connect/userinfo'.format(
        current_app.config['KEYCLOAK_URL'], current_app.config['KEYCLOAK_REALM']), headers=headers)
    profile = r.json()

    roles = profile['roles']
    login = profile['preferred_username']

    if not_authorized('ALLOWED_KEYCLOAK_ROLES', roles):
        raise ApiError('User %s is not authorized' % login, 403)

    customers = get_customers(login, groups=roles)

    token = create_token(profile['sub'], profile['name'], login, provider='keycloak', customers=customers, roles=roles)
    return jsonify(token=token.tokenize)
