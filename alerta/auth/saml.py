
import saml2.client
import saml2.config
import saml2.entity
import saml2.metadata
import saml2.saml

from flask import (Response, current_app, make_response, render_template,
                   request)
from flask_cors import cross_origin

from alerta.auth.utils import create_token, get_customers, not_authorized
from alerta.exceptions import ApiError
from alerta.models.permission import Permission
from alerta.models.user import User
from alerta.utils.audit import auth_audit_trail
from alerta.utils.collections import merge
from alerta.utils.response import absolute_url

from . import auth


def get_saml2_config():
    config = saml2.config.Config()

    saml_settings = {
        'metadata': {
            'remote': [{
                'url': current_app.config['SAML2_METADATA_URL'],
            }]
        },
        'entityid': absolute_url(),
        'service': {
            'sp': {
                'endpoints': {
                    'assertion_consumer_service': [
                        (absolute_url('/auth/saml'), saml2.BINDING_HTTP_POST)
                    ]
                },
                'allow_unsolicited': True,
                'authn_requests_signed': False,
                'want_assertions_signed': True,
                'want_response_signed': False
            }
        }
    }
    if current_app.config['SAML2_ENTITY_ID']:
        saml_settings['entityid'] = current_app.config['SAML2_ENTITY_ID']

    if current_app.config['SAML2_CONFIG'].get('metadata'):
        saml_settings['metadata'] = current_app.config['SAML2_CONFIG']['metadata']

    merge(saml_settings, current_app.config['SAML2_CONFIG'])  # allow settings override

    config.load(saml_settings)
    config.allow_unknown_attributes = True
    return config


def saml_client():
    return saml2.client.Saml2Client(
        config=get_saml2_config()
    )


@auth.route('/auth/saml', methods=['GET'])
def saml_redirect_to_idp():
    (session_id, result) = saml_client().prepare_for_authenticate(relay_state=request.referrer)
    return make_response('', 302, result['headers'])


@auth.route('/auth/saml', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def saml_response_from_idp():
    origin = request.form['RelayState']

    authn_response = saml_client().parse_authn_request_response(
        xmlstr=request.form['SAMLResponse'],
        binding=saml2.entity.BINDING_HTTP_POST
    )
    identity = authn_response.get_identity()
    subject = authn_response.get_subject()

    name = current_app.config['SAML2_USER_NAME_FORMAT'].format(**dict(map(lambda x: (x[0], x[1][0]), identity.items())))
    login = subject.text
    email = identity[current_app.config['SAML2_EMAIL_ATTRIBUTE']][0]

    # Create user if not yet there
    user = User.find_by_username(username=email)
    if not user:
        user = User(name=name, login=login, password='', email=email,
                    roles=[], text='SAML2 user', email_verified=True)
        try:
            user = user.create()
        except Exception as e:
            ApiError(str(e), 500)

    if user.status != 'active':
        raise ApiError('User {} is not active'.format(email), 403)

    groups = identity.get('groups', [])
    if not_authorized('ALLOWED_SAML2_GROUPS', groups) or not_authorized('ALLOWED_EMAIL_DOMAINS', groups=[user.domain]):
        message = {'status': 'error', 'message': 'User {} is not authorized'.format(email)}
        return render_template('auth/saml2.html', message=message, origin=origin), 403

    user.update_last_login()

    scopes = Permission.lookup(login=user.email, roles=user.roles + groups)
    customers = get_customers(login=user.email, groups=[user.domain] + groups)

    auth_audit_trail.send(current_app._get_current_object(), event='saml2-login', message='user login via SAML2',
                          user=user.email, customers=customers, scopes=scopes, resource_id=user.id, type='user',
                          request=request)

    token = create_token(user_id=user.id, name=user.name, login=user.email, provider='saml2', customers=customers,
                         scopes=scopes, roles=user.roles, email=user.email, email_verified=user.email_verified)

    message = {'status': 'ok', 'token': token.tokenize}
    return render_template('auth/saml2.html', message=message, origin=origin), 200


@auth.route('/auth/saml/metadata.xml', methods=['GET'])
def saml_metadata():
    descriptor = saml2.metadata.entity_descriptor(get_saml2_config())
    return Response(str(descriptor), content_type='text/xml; charset=utf-8')
