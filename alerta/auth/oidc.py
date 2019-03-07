
import requests
from flask import current_app, jsonify, request
from flask_cors import cross_origin

from alerta.auth.utils import create_token, get_customers, not_authorized
from alerta.exceptions import ApiError
from alerta.models.permission import Permission
from alerta.utils.audit import auth_audit_trail

from . import auth


def get_oidc_configuration(app):
    issuer_url = app.config['OIDC_ISSUER_URL']
    if not issuer_url:
        raise ApiError('Must define OIDC_ISSUER_URL setting in server configuration.', 503)
    discovery_doc_url = '{}/.well-known/openid-configuration'.format(issuer_url)

    r = requests.get(discovery_doc_url)
    config = r.json()

    if config['issuer'] != issuer_url:
        raise ApiError('Issuer Claim does not match Issuer URL used to retrieve OpenID configuration', 503)

    return config


@auth.route('/auth/openid', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def openid():

    oidc_configuration = get_oidc_configuration(current_app)
    token_endpoint = oidc_configuration['token_endpoint']
    userinfo_endpoint = oidc_configuration['userinfo_endpoint']

    data = {
        'grant_type': 'authorization_code',
        'code': request.json['code'],
        'redirect_uri': request.json['redirectUri'],
        'client_id': request.json['clientId'],
        'client_secret': current_app.config['OAUTH2_CLIENT_SECRET'],
    }
    r = requests.post(token_endpoint, data)
    token = r.json()

    headers = {'Authorization': '{} {}'.format(token.get('token_type', 'Bearer'), token['access_token'])}
    r = requests.get(userinfo_endpoint, headers=headers)
    userinfo = r.json()

    subject = userinfo['sub']
    name = userinfo.get('name')
    login = userinfo.get('preferred_username')
    email = userinfo.get('email')
    email_verified = userinfo.get('email_verified')
    roles = userinfo.get(current_app.config['OIDC_CUSTOM_CLAIM'], ['user'])

    if not_authorized('ALLOWED_OIDC_ROLES', roles):
        raise ApiError('User {} is not authorized'.format(login), 403)

    customers = get_customers(login, groups=roles)

    auth_audit_trail.send(current_app._get_current_object(), event='openid-login', message='user login via OpenID Connect',
                          user=login, customers=customers, scopes=Permission.lookup(login, groups=roles),
                          resource_id=subject, type='openid', request=request)

    token = create_token(user_id=subject, name=name, login=login, provider='openid', customers=customers,
                         roles=roles, email=email, email_verified=email_verified)
    return jsonify(token=token.tokenize)
