
import requests
from flask import current_app, jsonify, request
from flask_cors import cross_origin

from alerta.auth.utils import create_token, get_customers, not_authorized
from alerta.exceptions import ApiError

from . import auth


@auth.route('/auth/gitlab', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def gitlab():

    access_token_url = current_app.config['GITLAB_URL'] + '/oauth/token'
    tokeninfo_url = current_app.config['GITLAB_URL'] + '/oauth/token/info'
    userinfo_url = current_app.config['GITLAB_URL'] + '/oauth/userinfo'
    gitlab_api_url = current_app.config['GITLAB_URL'] + '/api/v4'

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
        return jsonify(status='error', message='Failed to call Gitlab API over HTTPS')
    token = r.json()

    headers = {'Authorization': 'Bearer ' + token['access_token']}
    r = requests.get(tokeninfo_url, headers=headers)
    scopes = r.json().get('scopes', [])
    current_app.logger.info('GitLab scopes: {}'.format(scopes))

    if 'openid' in scopes:
        r = requests.post(userinfo_url, headers=headers)
        profile = r.json()

        user_id = profile['sub']
        login = profile['nickname']
        groups = profile.get('groups', [])
        email_verified = profile.get('email_verified', False)
    else:
        r = requests.get(gitlab_api_url + '/user', headers=headers)
        profile = r.json()

        user_id = profile['id']
        login = profile['username']

        r = requests.get(gitlab_api_url + '/groups', headers=headers)
        groups = [g['path'] for g in r.json()]
        email_verified = True if profile.get('email', None) else False

    if not_authorized('ALLOWED_GITLAB_GROUPS', groups):
        raise ApiError('User %s is not authorized' % login, 403)

    customers = get_customers(login, groups)

    token = create_token(user_id, profile.get('name', '@' + login), login, provider='gitlab', customers=customers,
                         groups=groups, email=profile.get('email', None), email_verified=email_verified)
    return jsonify(token=token.tokenize)
