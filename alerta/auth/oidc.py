import json

import jwt
import requests
from flask import current_app, jsonify, request
from flask_cors import cross_origin
from jwt.algorithms import RSAAlgorithm  # type: ignore

from alerta.auth.utils import create_token, get_customers, not_authorized
from alerta.exceptions import ApiError
from alerta.models.permission import Permission
from alerta.models.user import User
from alerta.utils.audit import auth_audit_trail

from . import auth


def get_oidc_configuration(app):

    OIDC_ISSUER_URL_BY_PROVIDER = {
        'azure': 'https://sts.windows.net/{}/'.format(app.config['AZURE_TENANT']),
        'gitlab': app.config['GITLAB_URL'],
        'google': 'https://accounts.google.com',
        'keycloak': '{}/auth/realms/{}'.format(app.config['KEYCLOAK_URL'], app.config['KEYCLOAK_REALM'])
    }

    issuer_url = OIDC_ISSUER_URL_BY_PROVIDER.get(app.config['AUTH_PROVIDER']) or app.config['OIDC_ISSUER_URL']
    if not issuer_url:
        raise ApiError('Must define Issuer URL (OIDC_ISSUER_URL) in server configuration to use OpenID Connect.', 503)
    discovery_doc_url = issuer_url.strip('/') + '/.well-known/openid-configuration'

    try:
        r = requests.get(discovery_doc_url)
        config = r.json()
    except Exception as e:
        raise ApiError('Could not get OpenID configuration from well known URL: {}'.format(str(e)), 503)

    if config['issuer'] != issuer_url:
        raise ApiError('Issuer Claim does not match Issuer URL used to retrieve OpenID configuration', 503)

    if app.config['OIDC_VERIFY_TOKEN']:
        try:
            jwks_uri = config['jwks_uri']
            r = requests.get(jwks_uri)
            keys = {k['kid']: RSAAlgorithm.from_jwk(json.dumps(k)) for k in r.json()['keys']}
        except Exception as e:
            raise ApiError('Could not get OpenID JWT Key Set from JWKS URL: {}'.format(str(e)), 503)
    else:
        keys = {}

    return config, keys


@auth.route('/auth/openid', methods=['OPTIONS', 'POST'])
@auth.route('/auth/azure', methods=['OPTIONS', 'POST'])
@auth.route('/auth/gitlab', methods=['OPTIONS', 'POST'])
@auth.route('/auth/google', methods=['OPTIONS', 'POST'])
@auth.route('/auth/keycloak', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def openid():

    oidc_configuration, jwt_key_set = get_oidc_configuration(current_app)
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

    try:
        if current_app.config['OIDC_VERIFY_TOKEN']:
            jwt_header = jwt.get_unverified_header(token['id_token'])
            public_key = jwt_key_set[jwt_header['kid']]

            id_token = jwt.decode(
                token['id_token'],
                key=public_key,
                algorithms=jwt_header['alg']
            )
        else:
            id_token = jwt.decode(
                token['id_token'],
                verify=False
            )
    except Exception:
        current_app.logger.warning('No ID token in OpenID Connect token response.')
        id_token = {}

    try:
        headers = {'Authorization': '{} {}'.format(token.get('token_type', 'Bearer'), token['access_token'])}
        r = requests.get(userinfo_endpoint, headers=headers)
        userinfo = r.json()
    except Exception:
        raise ApiError('No access token in OpenID Connect token response.')

    subject = userinfo['sub']
    name = userinfo.get('name') or id_token.get('name')
    nickname = userinfo.get('nickname')
    email = userinfo.get('email') or id_token.get('email')
    email_verified = userinfo.get('email_verified', id_token.get('email_verified', bool(email)))
    picture = userinfo.get('picture') or id_token.get('picture')

    role_claim = current_app.config['OIDC_ROLE_CLAIM']
    group_claim = current_app.config['OIDC_GROUP_CLAIM']
    custom_claims = {
        role_claim: userinfo.get(role_claim) or id_token.get(role_claim, []),
        group_claim: userinfo.get(group_claim) or id_token.get(group_claim, []),
    }

    login = userinfo.get('preferred_username', nickname or email)
    if not login:
        raise ApiError("Must support one of the following OpenID claims: 'preferred_username', 'nickname' or 'email'", 400)

    user = User.find_by_id(id=subject)
    if not user:
        user = User(id=subject, name=name, login=login, password='', email=email,
                    roles=[], text='', email_verified=email_verified)
        user.create()
    else:
        user.update(login=login, email=email)

    roles = custom_claims[role_claim] or user.roles
    groups = custom_claims[group_claim]

    if user.status != 'active':
        raise ApiError('User {} is not active'.format(login), 403)

    if not_authorized('ALLOWED_OIDC_ROLES', roles) and not_authorized('ALLOWED_EMAIL_DOMAINS', groups=[user.domain]):
        raise ApiError('User {} is not authorized'.format(login), 403)
    user.update_last_login()

    scopes = Permission.lookup(login, roles)
    customers = get_customers(login, groups=[user.domain] + groups)

    auth_audit_trail.send(current_app._get_current_object(), event='openid-login', message='user login via OpenID Connect',
                          user=login, customers=customers, scopes=scopes, resource_id=subject, type='user', request=request)

    token = create_token(user_id=subject, name=name, login=login, provider='openid', customers=customers,
                         scopes=scopes, email=email, email_verified=email_verified, picture=picture, **custom_claims)
    return jsonify(token=token.tokenize)
