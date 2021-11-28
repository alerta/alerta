import requests
from flask import current_app, jsonify, request
from flask_cors import cross_origin

from alerta.auth.utils import create_token, get_customers, not_authorized
from alerta.exceptions import ApiError
from alerta.models.permission import Permission
from alerta.models.user import User
from alerta.utils.audit import auth_audit_trail

from . import auth


@auth.route('/auth/github', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def github():

    if current_app.config['GITHUB_URL'] == 'https://github.com':
        token_endpoint = 'https://github.com/login/oauth/access_token'
        github_api_url = 'https://api.github.com'
    else:
        token_endpoint = current_app.config['GITHUB_URL'] + '/login/oauth/access_token'
        github_api_url = current_app.config['GITHUB_URL'] + '/api/v3'

    client_lookup = dict(zip(
        current_app.config['OAUTH2_CLIENT_ID'].split(','),
        current_app.config['OAUTH2_CLIENT_SECRET'].split(',')
    ))
    client_secret = client_lookup.get(request.json['clientId'], None)
    data = {
        'grant_type': 'authorization_code',
        'code': request.json['code'],
        'redirect_uri': request.json['redirectUri'],
        'client_id': request.json['clientId'],
        'client_secret': client_secret,
    }
    r = requests.post(token_endpoint, data, headers={'Accept': 'application/json'})
    token = r.json()

    try:
        headers = {'Authorization': f"token {token['access_token']}"}
        r = requests.get(github_api_url + '/user', headers=headers)
        profile = r.json()
    except Exception:
        raise ApiError('No access token in OpenID Connect token response.')

    r = requests.get(github_api_url + '/user/teams', headers=headers)  # list public and private Github orgs
    profile['teams'] = [f"{t['organization']['login']}/{t['slug']}" for t in r.json()]

    r = requests.get(github_api_url + '/user/orgs', headers=headers)  # list public and private Github orgs
    profile['organizations'] = [o['login'] for o in r.json()]

    subject = str(profile['id'])
    name = profile['name']
    username = '@' + profile['login']
    email = profile['email']
    email_verified = bool(email)
    picture = profile['avatar_url']

    role_claim = current_app.config['GITHUB_ROLE_CLAIM']
    group_claim = current_app.config['GITHUB_GROUP_CLAIM']
    custom_claims = {
        role_claim: profile.get(role_claim, []),
        group_claim: profile.get(group_claim, []),
    }

    login = username or email
    if not login:
        raise ApiError("Must allow access to GitHub user profile information: 'login' or 'email'", 400)

    user = User.find_by_id(id=subject)
    if not user:
        user = User(id=subject, name=name, login=login, password='', email=email,
                    roles=current_app.config['USER_ROLES'], text='', email_verified=email_verified)
        user.create()
    else:
        user.update(login=login, email=email)

    roles = custom_claims[role_claim] + user.roles
    groups = custom_claims[group_claim]

    if user.status != 'active':
        raise ApiError(f'User {login} is not active', 403)

    if not_authorized('ALLOWED_GITHUB_ORGS', profile['organizations']) or not_authorized('ALLOWED_EMAIL_DOMAINS', groups=[user.domain]):
        raise ApiError(f'User {login} is not authorized', 403)
    user.update_last_login()

    scopes = Permission.lookup(login, roles=roles)
    customers = get_customers(login, groups=groups + ([user.domain] if user.domain else []))

    auth_audit_trail.send(current_app._get_current_object(), event='github-login', message='user login via GitHub',
                          user=login, customers=customers, scopes=scopes, roles=user.roles, **custom_claims,
                          resource_id=subject, type='user', request=request)

    token = create_token(user_id=subject, name=name, login=login, provider='github',
                         customers=customers, scopes=scopes, roles=user.roles, groups=profile['teams'], orgs=profile['organizations'],
                         email=email, email_verified=email_verified, picture=picture)
    return jsonify(token=token.tokenize())
