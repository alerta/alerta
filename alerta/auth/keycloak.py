
import requests
from flask import current_app, request, jsonify
from flask_cors import cross_origin

from alerta.auth.utils import is_authorized, create_token, get_customer
from alerta.exceptions import ApiError
from . import auth


@auth.route('/auth/keycloak', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def keycloak():

    if not current_app.config['KEYCLOAK_URL']:
        return jsonify(status="error", message="Must define KEYCLOAK_URL setting in server configuration."), 503

    access_token_url = "{0}/auth/realms/{1}/protocol/openid-connect/token".format(current_app.config['KEYCLOAK_URL'], current_app.config['KEYCLOAK_REALM'])

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
        return jsonify(status="error", message="Failed to call Keycloak API over HTTPS")
    access_token = r.json()

    headers = {"Authorization": "{0} {1}".format(access_token['token_type'], access_token['access_token'])}
    r = requests.get("{0}/auth/realms/{1}/protocol/openid-connect/userinfo".format(current_app.config['KEYCLOAK_URL'], current_app.config['KEYCLOAK_REALM']), headers=headers)
    profile = r.json()

    roles = profile['roles']
    login = profile['preferred_username']

    if is_authorized('ALLOWED_KEYCLOAK_ROLES', roles):
        raise ApiError("User %s is not authorized" % login, 403)

    customer = get_customer(login, groups=roles)

    token = create_token(profile['sub'], profile['name'], login, provider='keycloak', customer=customer, roles=roles)
    return jsonify(token=token.tokenize)
