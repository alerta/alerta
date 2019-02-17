
import jwt
import requests
from flask import current_app, jsonify, request
from flask_cors import cross_origin

from alerta.auth.utils import create_token, get_customers, not_authorized
from alerta.exceptions import ApiError
from alerta.models.permission import Permission
from alerta.utils.audit import auth_audit_trail

from . import auth


@auth.route('/auth/azure', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def azure():

    if not current_app.config['AZURE_TENANT']:
        raise ApiError('Must define AZURE_TENANT setting in server configuration.', 503)

    discovery_doc_url = 'https://login.microsoftonline.com/{}/.well-known/openid-configuration'.format(
        current_app.config['AZURE_TENANT']
    )

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

    if not_authorized('ALLOWED_EMAIL_DOMAINS', groups=[domain]):
        raise ApiError('User %s is not authorized' % email, 403)

    customers = get_customers(email, groups=[domain])

    auth_audit_trail.send(current_app._get_current_object(), event='azure-login', message='user login via Azure',
                          user=email, customers=customers, scopes=Permission.lookup(email, groups=[domain]),
                          resource_id=subject, type='azure', request=request)

    token = create_token(user_id=subject, name=name, login=email, provider='azure', customers=customers,
                         orgs=[domain], email=email)
    return jsonify(token=token.tokenize)
