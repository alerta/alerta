
import requests
from flask import current_app, jsonify, request
from flask_cors import cross_origin

from alerta.auth.utils import create_token, get_customers, not_authorized
from alerta.exceptions import ApiError
from alerta.models.token import Jwt

from . import auth


@auth.route('/auth/google', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def google():
    access_token_url = 'https://accounts.google.com/o/oauth2/token'
    people_api_url = 'https://www.googleapis.com/plus/v1/people/me/openIdConnect'

    payload = {
        'client_id': request.json['clientId'],
        'client_secret': current_app.config['OAUTH2_CLIENT_SECRET'],
        'redirect_uri': request.json['redirectUri'],
        'grant_type': 'authorization_code',
        'code': request.json['code'],
    }
    r = requests.post(access_token_url, data=payload)
    token = r.json()

    id_token = Jwt.parse(
        token['id_token'],
        key='',
        verify=False,
        algorithm='RS256'
    )

    domain = id_token.email.split('@')[1]

    if not_authorized('ALLOWED_EMAIL_DOMAINS', groups=[domain]):
        raise ApiError('User %s is not authorized' % id_token.email, 403)

    # Get Google+ profile for Full name
    headers = {'Authorization': 'Bearer ' + token['access_token']}
    r = requests.get(people_api_url, headers=headers)
    profile = r.json()

    if not profile:
        raise ApiError('Google+ API is not enabled for this Client ID', 400)

    customers = get_customers(id_token.email, groups=[domain])

    name = profile.get('name', id_token.email.split('@')[0])
    token = create_token(id_token.subject, name, id_token.email, provider='google', customers=customers,
                         orgs=[domain], email=id_token.email, email_verified=id_token.email_verified)
    return jsonify(token=token.tokenize)
