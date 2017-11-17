
import requests
from flask import current_app, request, jsonify
from flask_cors import cross_origin

from alerta.auth.utils import is_authorized, create_token, get_customer
from alerta.exceptions import ApiError
from . import auth


@auth.route('/auth/github', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def github():

    if current_app.config['GITHUB_URL']:
        access_token_url = current_app.config['GITHUB_URL'] + '/login/oauth/access_token'
        github_api_url = current_app.config['GITHUB_URL'] + '/api/v3'
    else:
        access_token_url = 'https://github.com/login/oauth/access_token'
        github_api_url = 'https://api.github.com'

    params = {
        'client_id': request.json['clientId'],
        'redirect_uri': request.json['redirectUri'],
        'client_secret': current_app.config['OAUTH2_CLIENT_SECRET'],
        'code': request.json['code']
    }

    headers = {'Accept': 'application/json'}
    r = requests.get(access_token_url, headers=headers, params=params)
    access_token = r.json()

    r = requests.get(github_api_url+'/user', params=access_token)
    profile = r.json()

    r = requests.get(github_api_url+'/user/orgs', params=access_token)  # list public and private Github orgs
    organizations = [o['login'] for o in r.json()]
    login = profile['login']

    if is_authorized('ALLOWED_GITHUB_ORGS', organizations):
        raise ApiError("User %s is not authorized" % login, 403)

    customer = get_customer(login, organizations)

    token = create_token(profile['id'], profile.get('name', '@'+login), login, provider='github', customer=customer,
                         orgs=organizations, email=profile.get('email', None), email_verified=True if 'email' in profile else False)
    return jsonify(token=token.tokenize)
