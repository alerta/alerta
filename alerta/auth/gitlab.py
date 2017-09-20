
import requests
from flask import current_app, request, jsonify
from flask_cors import cross_origin

from alerta.auth.utils import is_authorized, create_token, get_customer
from alerta.exceptions import ApiError
from . import auth


@auth.route('/auth/gitlab', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def gitlab():

    access_token_url = current_app.config['GITLAB_URL'] + '/oauth/token'
    gitlab_api_url = current_app.config['GITLAB_URL'] + '/api/v3'

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
    access_token = r.json()

    r = requests.get(gitlab_api_url+'/user', params=access_token)
    profile = r.json()

    r = requests.get(gitlab_api_url+'/groups', params=access_token)
    groups = [g['path'] for g in r.json()]
    login = profile['username']

    if is_authorized('ALLOWED_GITLAB_GROUPS', groups):
        raise ApiError("User %s is not authorized" % login, 403)

    customer = get_customer(login, groups)

    token = create_token(profile['id'], profile.get('name', '@'+login), login, provider='gitlab', customer=customer,
                         groups=groups, email=profile.get('email', None), email_verified=True if profile.get('email', None) else False)
    return jsonify(token=token.tokenize)
