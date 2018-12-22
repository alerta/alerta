
import jwt
import requests
from flask import current_app, jsonify, request
from flask_cors import cross_origin

from alerta.auth.utils import create_token, get_customers, not_authorized
from alerta.exceptions import ApiError
from alerta.models.permission import Permission
from alerta.utils.audit import auth_audit_trail

from . import auth


@auth.route('/auth/google', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def google():
    discovery_doc_url = 'https://accounts.google.com/.well-known/openid-configuration'

    r = requests.get(discovery_doc_url)
    token_endpoint = r.json()['token_endpoint']

    data = {
        'code': request.json['code'],
        'client_id': request.json['clientId'],
        'client_secret': current_app.config['OAUTH2_CLIENT_SECRET'],
        'redirect_uri': request.json['redirectUri'],
        'grant_type': 'authorization_code'
    }
    r = requests.post(token_endpoint, data)
    token = r.json()

    id_token = jwt.decode(
        token['id_token'],
        verify=False
    )

    subject = id_token['sub']
    name = id_token['name']
    email = id_token['email']
    domain = email.split('@')[1]
    email_verified = id_token['email_verified']

    if not_authorized('ALLOWED_EMAIL_DOMAINS', groups=[domain]):
        raise ApiError('User %s is not authorized' % email, 403)

    customers = get_customers(email, groups=[domain])

    auth_audit_trail.send(current_app._get_current_object(), event='google-login', message='user login via Google',
                          user=email, customers=customers, scopes=Permission.lookup(email, groups=[domain]),
                          resource_id=subject, type='google', request=request)

    token = create_token(user_id=subject, name=name, login=email, provider='google', customers=customers,
                         orgs=[domain], email=email, email_verified=email_verified)
    return jsonify(token=token.tokenize)
