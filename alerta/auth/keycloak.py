
import requests
from flask import current_app, jsonify, request
from flask_cors import cross_origin

from alerta.auth.utils import create_token, get_customers, not_authorized
from alerta.exceptions import ApiError
from alerta.models.permission import Permission
from alerta.utils.audit import auth_audit_trail

from . import auth


@auth.route('/auth/keycloak', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def keycloak():

    if not current_app.config['KEYCLOAK_URL']:
        raise ApiError('Must define KEYCLOAK_URL setting in server configuration.', 503)

    discovery_doc_url = '{keycloak_url}/auth/realms/{realm_name}/.well-known/openid-configuration'.format(
        keycloak_url=current_app.config['KEYCLOAK_URL'],
        realm_name=current_app.config['KEYCLOAK_REALM']
    )

    r = requests.get(discovery_doc_url)
    token_endpoint = r.json()['token_endpoint']
    userinfo_endpoint = r.json()['userinfo_endpoint']

    data = {
        'code': request.json['code'],
        'client_id': request.json['clientId'],
        'client_secret': current_app.config['OAUTH2_CLIENT_SECRET'],
        'redirect_uri': request.json['redirectUri'],
        'grant_type': 'authorization_code'
    }
    r = requests.post(token_endpoint, data)
    token = r.json()

    headers = {'Authorization': '{} {}'.format(token['token_type'], token['access_token'])}
    r = requests.get(userinfo_endpoint, headers=headers)
    profile = r.json()

    subject = profile['sub']
    name = profile.get('name')
    email = profile.get('email')
    email_verified = profile.get('email_verified')
    login = profile.get('preferred_username')
    roles = profile.get('roles', ['user'])

    if not_authorized('ALLOWED_KEYCLOAK_ROLES', roles):
        raise ApiError('User %s is not authorized' % login, 403)

    customers = get_customers(login, groups=roles)

    auth_audit_trail.send(current_app._get_current_object(), event='keycloak-login', message='user login via Keycloak',
                          user=login, customers=customers, scopes=Permission.lookup(login, groups=roles),
                          resource_id=subject, type='keycloak', request=request)

    token = create_token(user_id=subject, name=name, login=login, provider='keycloak', customers=customers,
                         roles=roles, email=email, email_verified=email_verified)
    return jsonify(token=token.tokenize)
