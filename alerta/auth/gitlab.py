
import requests
from flask import current_app, request, jsonify
from flask_cors import cross_origin

from alerta.auth.utils import not_authorized, create_token, get_customers
from alerta.exceptions import ApiError
from . import auth


@auth.route('/auth/gitlab', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def gitlab():

    access_token_url = current_app.config['GITLAB_URL'] + '/oauth/token'
    tokeninfo_url = current_app.config['GITLAB_URL'] + '/oauth/token/info'
    userinfo_url = current_app.config['GITLAB_URL'] + '/oauth/userinfo'

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
        return jsonify(status="error", message="Failed to call Gitlab API over HTTPS")
    token = r.json()

    headers = {'Authorization': 'Bearer ' + token['access_token']}
    r = requests.get(tokeninfo_url, headers=headers)
    scopes = r.json().get('scopes', [])
    if 'openid' not in scopes:
        raise ApiError("GitLab OAuth2 application scopes must include 'openid'", 403)

    r = requests.post(userinfo_url, headers=headers)
    profile = r.json()
    current_app.logger.info(profile)

    login = profile['nickname']
    groups = profile.get('groups', [])

    if not_authorized('ALLOWED_GITLAB_GROUPS', groups):
        raise ApiError("User %s is not authorized" % login, 403)

    customers = get_customers(login, groups)

    token = create_token(profile['sub'], profile.get('name', '@'+login), login, provider='gitlab', customers=customers,
                         groups=groups, email=profile.get('email', None), email_verified=profile.get('email_verified', False))
    return jsonify(token=token.tokenize)
