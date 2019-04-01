
import requests
from flask import current_app, jsonify, request
from flask_cors import cross_origin

from alerta.auth.utils import create_token, get_customers, not_authorized
from alerta.exceptions import ApiError
from alerta.models.permission import Permission
from alerta.utils.audit import auth_audit_trail

from . import auth


@auth.route('/auth/github', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def github():

    if current_app.config['GITHUB_URL'] == 'https://github.com':
        access_token_url = 'https://github.com/login/oauth/access_token'
        github_api_url = 'https://api.github.com'
    else:
        access_token_url = current_app.config['GITHUB_URL'] + '/login/oauth/access_token'
        github_api_url = current_app.config['GITHUB_URL'] + '/api/v3'

    client_lookup = dict(zip(
        current_app.config['OAUTH2_CLIENT_ID'].split(','),
        current_app.config['OAUTH2_CLIENT_SECRET'].split(',')
    ))
    client_secret = client_lookup.get(request.json['clientId'], None)
    params = {
        'client_id': request.json['clientId'],
        'redirect_uri': request.json['redirectUri'],
        'client_secret': client_secret,
        'code': request.json['code']
    }

    headers = {'Accept': 'application/json'}
    r = requests.get(access_token_url, headers=headers, params=params)
    access_token = r.json()

    r = requests.get(github_api_url + '/user', params=access_token)
    profile = r.json()

    r = requests.get(github_api_url + '/user/orgs', params=access_token)  # list public and private Github orgs
    organizations = [o['login'] for o in r.json()]
    login = profile['login']

    if not_authorized('ALLOWED_GITHUB_ORGS', organizations):
        raise ApiError('User %s is not authorized' % login, 403)

    scopes = Permission.lookup(login, roles=organizations)
    customers = get_customers(login, groups=organizations)

    auth_audit_trail.send(current_app._get_current_object(), event='github-login', message='user login via GitHub',
                          user=login, customers=customers, scopes=scopes,
                          resource_id=profile['id'], type='github', request=request)

    token = create_token(user_id=profile['id'], name=profile.get('name', '@' + login), login=login, provider='github',
                         customers=customers, scopes=scopes, orgs=organizations, email=profile.get('email', None),
                         email_verified=True if 'email' in profile else False)
    return jsonify(token=token.tokenize)
