
import jwt
import requests
import bcrypt
import re

try:
    import simplejson as json
except ImportError:
    import json

from datetime import datetime, timedelta
from functools import wraps
from flask import g, request, render_template, jsonify, make_response
from flask_cors import cross_origin
from jwt import DecodeError, ExpiredSignature, InvalidAudience
from base64 import urlsafe_b64decode
from uuid import uuid4

try:
    import saml2
    import saml2.entity
    import saml2.metadata
    import saml2.config
    import saml2.client
    import saml2.saml
except ImportError:
    pass  # saml2 authentication will not work

import smtplib
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    from urllib.parse import parse_qsl, urlencode
except ImportError:
    from urlparse import parse_qsl
    from urllib import urlencode

from alerta.app import app, db
from alerta.app.utils import absolute_url, deepmerge

BASIC_AUTH_REALM = "Alerta"

LOG = app.logger


class AuthError(Exception):
    pass


class Forbidden(Exception):
    pass


def verify_api_key(key):
    key_info = db.is_key_valid(key)
    if not key_info:
        raise AuthError("API key '%s' is invalid" % key)
    db.update_key(key)
    return key_info


def create_token(user, name, login, provider, customer, scopes):
    payload = {
        'iss': request.url_root,
        'sub': user,
        'iat': datetime.utcnow(),
        'aud': app.config['OAUTH2_CLIENT_ID'] or request.url_root,
        'exp': datetime.utcnow() + timedelta(days=app.config['TOKEN_EXPIRE_DAYS']),
        'name': name,
        'login': login,
        'provider': provider,
        'scope': ' '.join(scopes)
    }

    if app.config['CUSTOMER_VIEWS']:
        payload['customer'] = customer

    if provider == 'basic':
        payload['email_verified'] = db.is_email_verified(login)

    token = jwt.encode(payload, key=app.config['SECRET_KEY'])
    return token.decode('unicode_escape')


def parse_token(token):
    return jwt.decode(token, key=app.config['SECRET_KEY'], audience=app.config['OAUTH2_CLIENT_ID'] or request.url_root)


def authenticate(message, status_code=401):
    return jsonify(status="error", message=message), status_code


def is_in_scope(scope):
    if scope in g.scopes or scope.split(':')[0] in g.scopes:
        return True
    elif scope.startswith('read'):
        return is_in_scope(scope.replace('read', 'write'))
    elif scope.startswith('write'):
        return is_in_scope(scope.replace('write', 'admin'))
    else:
        return False


def permission(scope):
    def decorated(f):
        @wraps(f)
        def wrapped(*args, **kwargs):

            auth_header = request.headers.get('Authorization', '')
            m = re.match('Key (\S+)', auth_header)
            key = m.group(1) if m else request.args.get('api-key', None)

            if key:
                try:
                    ki = verify_api_key(key)
                except AuthError as e:
                    return authenticate(str(e), 401)
                except Forbidden as e:
                    return authenticate(str(e), 403)
                except Exception as e:
                    return authenticate(str(e), 500)
                g.user = ki['user']
                g.customer = ki.get('customer', None)
                g.scopes = ki['scopes']

                if is_in_scope(scope):
                    return f(*args, **kwargs)
                else:
                    return authenticate('Missing required scope: %s' % scope, 403)

            auth_header = request.headers.get('Authorization', '')
            m = re.match('Bearer (\S+)', auth_header)
            token = m.group(1) if m else None

            if token:
                try:
                    payload = parse_token(token)
                except DecodeError:
                    return authenticate('Token is invalid')
                except ExpiredSignature:
                    return authenticate('Token has expired')
                except InvalidAudience:
                    return authenticate('Invalid audience')
                g.user = payload['login']
                g.customer = payload.get('customer', None)
                g.scopes = payload.get('scope', '').split(' ')

                if is_in_scope(scope):
                    return f(*args, **kwargs)
                else:
                    return authenticate('Missing required scope: %s' % scope, 403)

            if not app.config['AUTH_REQUIRED']:
                return f(*args, **kwargs)

            return authenticate('Missing authorization API Key or Bearer Token')

        return wrapped
    return decorated


def scopes(user, groups):
    return db.get_scopes_by_match(user, groups)


class NoCustomerMatch(KeyError):
    pass


def customer_match(user, groups):
    if 'admin' in scopes(user, groups):
        return None
    else:
        match = db.get_customer_by_match([user] + groups)
        if match:
            if match == '*':
                return None
            return match
        else:
            raise NoCustomerMatch


@app.route('/auth/login', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def login():
    try:
        email = request.json['email']
        domain = email.split('@')[1]
        password = request.json['password']
    except KeyError:
        return jsonify(status="error", message="Must supply 'email' and 'password'"), 401, \
            {'WWW-Authenticate': 'Basic realm="%s"' % BASIC_AUTH_REALM}

    if app.config['AUTH_REQUIRED'] and not db.is_user_valid(login=email):
        return jsonify(status="error", message="User or password not valid"), 401, \
            {'WWW-Authenticate': 'Basic realm="%s"' % BASIC_AUTH_REALM}
    elif not db.is_user_valid(login=email):
        return jsonify(status="error", message="User %s does not exist" % email), 401, \
            {'WWW-Authenticate': 'Basic realm="%s"' % BASIC_AUTH_REALM}
    else:
        user = db.get_users(query={"login": email}, password=True)[0]

    if not bcrypt.hashpw(password.encode('utf-8'), user['password'].encode('utf-8')) == user['password'].encode('utf-8'):
        return jsonify(status="error", message="User or password not valid"), 401, \
            {'WWW-Authenticate': 'Basic realm="%s"' % BASIC_AUTH_REALM}

    if app.config['EMAIL_VERIFICATION'] and not db.is_email_verified(email):
        return jsonify(status="error", message="email address %s has not been verified" % email), 401

    if app.config['AUTH_REQUIRED'] and not ('*' in app.config['ALLOWED_EMAIL_DOMAINS']
            or domain in app.config['ALLOWED_EMAIL_DOMAINS']):
        return jsonify(status="error", message="Login for user domain %s not allowed" % domain), 403

    if app.config['CUSTOMER_VIEWS']:
        try:
            customer = customer_match(email, groups=[domain])
        except NoCustomerMatch:
            return jsonify(status="error", message="No customer lookup defined for user domain %s" % domain), 403
    else:
        customer = None

    token = create_token(user['id'], user['name'], email, provider='basic', customer=customer, scopes=scopes(email, groups=[user['role']]))
    return jsonify(token=token)


@app.route('/auth/signup', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def signup():

    if request.json and 'name' in request.json:
        name = request.json["name"]
        email = request.json["email"]
        domain = email.split('@')[1]
        password = request.json["password"]
        provider = request.json.get("provider", "basic")
        role = 'admin' if email in app.config.get('ADMIN_USERS') else 'user'
        text = request.json.get("text", "")
        try:
            user = db.create_user(name, email, password, provider, role, text, email_verified=False)
        except Exception as e:
            return jsonify(status="error", message=str(e)), 500
    else:
        return jsonify(status="error", message="Must supply user 'name', 'email' and 'password' as parameters"), 400

    if not user:
        return jsonify(status="error", message="User with email '%s' already exists" % email), 409

    if app.config['EMAIL_VERIFICATION']:
        send_confirmation(name, email)
        if not db.is_email_verified(email):
            return jsonify(status="error", message="email address '%s' has not been verified" % email), 401

    if app.config['AUTH_REQUIRED'] and not ('*' in app.config['ALLOWED_EMAIL_DOMAINS']
            or domain in app.config['ALLOWED_EMAIL_DOMAINS']):
        return jsonify(status="error", message="Login for user domain '%s' not allowed" % domain), 403

    if app.config['CUSTOMER_VIEWS']:
        try:
            customer = customer_match(email, groups=[domain])
        except NoCustomerMatch:
            return jsonify(status="error", message="No customer lookup defined for user domain '%s'" % domain), 403
    else:
        customer = None

    token = create_token(user['id'], user['name'], email, provider, customer, scopes=scopes(email, groups=[role]))
    return jsonify(token=token)


def send_confirmation(name, email):

    msg = MIMEMultipart('related')
    msg['Subject'] = "[Alerta] Please verify your email '%s'" % email
    msg['From'] = app.config['MAIL_FROM']
    msg['To'] = email
    msg.preamble = "[Alerta] Please verify your email '%s'" % email

    confirm_hash = str(uuid4())
    db.set_user_hash(email, confirm_hash)

    text = 'Hello {name}!\n\n' \
           'Please verify your email address is {email} by clicking on the link below:\n\n' \
           '{url}\n\n' \
           'You\'re receiving this email because you recently created a new Alerta account.' \
           ' If this wasn\'t you, please ignore this email.'.format(
               name=name, email=email, url=absolute_url('/auth/confirm/' + confirm_hash))

    msg_text = MIMEText(text, 'plain', 'utf-8')
    msg.attach(msg_text)

    try:
        mx = smtplib.SMTP(app.config['SMTP_HOST'], app.config['SMTP_PORT'])
        if app.config['DEBUG']:
            mx.set_debuglevel(True)
        mx.ehlo()
        mx.starttls()
        mx.login(app.config['MAIL_FROM'], app.config['SMTP_PASSWORD'])
        mx.sendmail(app.config['MAIL_FROM'], [email], msg.as_string())
        mx.close()
    except (socket.error, socket.herror, socket.gaierror) as e:
        LOG.error('Mail server connection error: %s', str(e))
        return
    except smtplib.SMTPException as e:
        LOG.error('Failed to send email : %s', str(e))
    except Exception as e:
        LOG.error('Unhandled exception: %s', str(e))


@app.route('/auth/confirm/<hash>', methods=['GET'])
def verify_email(hash):

    email = db.is_hash_valid(hash)
    if email:
        db.validate_user(email)
        return render_template('auth/verify_success.html', email=email)
    else:
        return render_template('auth/verify_failed.html')


@app.route('/auth/google', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def google():
    access_token_url = 'https://accounts.google.com/o/oauth2/token'
    people_api_url = 'https://www.googleapis.com/plus/v1/people/me/openIdConnect'

    payload = {
        'client_id': request.json['clientId'],
        'client_secret': app.config['OAUTH2_CLIENT_SECRET'],
        'redirect_uri': request.json['redirectUri'],
        'grant_type': 'authorization_code',
        'code': request.json['code'],
    }

    try:
        r = requests.post(access_token_url, data=payload)
    except Exception:
        return jsonify(status="error", message="Failed to call Google API over HTTPS")
    token = r.json()

    if 'id_token' not in token:
        return jsonify(status="error", message=token.get('error', "Invalid token"))

    id_token = token['id_token'].split('.')[1].encode('ascii', 'ignore')
    id_token += '=' * (4 - (len(id_token) % 4))
    claims = json.loads(urlsafe_b64decode(id_token))

    if claims.get('aud') != app.config['OAUTH2_CLIENT_ID']:
        return jsonify(status="error", message="Token client audience is invalid"), 400

    email = claims.get('email')
    if app.config['AUTH_REQUIRED'] and not ('*' in app.config['ALLOWED_EMAIL_DOMAINS']
            or email.split('@')[1] in app.config['ALLOWED_EMAIL_DOMAINS']):
        return jsonify(status="error", message="User %s is not authorized" % email), 403

    headers = {'Authorization': 'Bearer ' + token['access_token']}
    r = requests.get(people_api_url, headers=headers)
    profile = r.json()

    if app.config['CUSTOMER_VIEWS']:
        try:
            customer = customer_match(email, groups=[email.split('@')[1]])
        except NoCustomerMatch:
            return jsonify(status="error", message="No customer lookup defined for user %s" % email), 403
    else:
        customer = None

    try:
        token = create_token(profile['sub'], profile['name'], email, provider='google',
                             customer=customer, scopes=scopes(email, groups=[email.split('@')[1]]))
    except KeyError:
        return jsonify(status="error", message="Google+ API is not enabled for this Client ID")

    return jsonify(token=token)


@app.route('/auth/github', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def github():

    if app.config['GITHUB_URL']:
        access_token_url = app.config['GITHUB_URL'] + '/login/oauth/access_token'
        github_api_url = app.config['GITHUB_URL'] + '/api/v3'
    else:
        access_token_url = 'https://github.com/login/oauth/access_token'
        github_api_url = 'https://api.github.com'

    params = {
        'client_id': request.json['clientId'],
        'redirect_uri': request.json['redirectUri'],
        'client_secret': app.config['OAUTH2_CLIENT_SECRET'],
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

    if app.config['AUTH_REQUIRED'] and not ('*' in app.config['ALLOWED_GITHUB_ORGS']
            or set(app.config['ALLOWED_GITHUB_ORGS']).intersection(set(organizations))):
        return jsonify(status="error", message="User %s is not authorized" % login), 403

    if app.config['CUSTOMER_VIEWS']:
        try:
            customer = customer_match(login, organizations)
        except NoCustomerMatch:
            return jsonify(status="error", message="No customer lookup defined for user %s" % login), 403
    else:
        customer = None

    token = create_token(profile['id'], profile.get('name', None) or '@'+login, login, provider='github',
                         customer=customer, scopes=scopes(login, groups=organizations))
    return jsonify(token=token)


@app.route('/auth/gitlab', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def gitlab():

    if not app.config['GITLAB_URL']:
        return jsonify(status="error", message="Must define GITLAB_URL setting in server configuration."), 503

    access_token_url = app.config['GITLAB_URL'] + '/oauth/token'
    gitlab_api_url = app.config['GITLAB_URL'] + '/api/v3'

    payload = {
        'client_id': request.json['clientId'],
        'client_secret': app.config['OAUTH2_CLIENT_SECRET'],
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

    if app.config['AUTH_REQUIRED'] and not ('*' in app.config['ALLOWED_GITLAB_GROUPS']
            or set(app.config['ALLOWED_GITLAB_GROUPS']).intersection(set(groups))):
        return jsonify(status="error", message="User %s is not authorized" % login), 403

    if app.config['CUSTOMER_VIEWS']:
        try:
            customer = customer_match(login, groups)
        except NoCustomerMatch:
            return jsonify(status="error", message="No customer lookup defined for user %s" % login), 403
    else:
        customer = None

    token = create_token(profile['id'], profile.get('name', None) or '@'+login, login, provider='gitlab',
                         customer=customer, scopes=scopes(login, groups))
    return jsonify(token=token)


@app.route('/auth/keycloak', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def keycloak():

    if not app.config['KEYCLOAK_URL']:
        return jsonify(status="error", message="Must define KEYCLOAK_URL setting in server configuration."), 503

    access_token_url = "{0}/auth/realms/{1}/protocol/openid-connect/token".format(app.config['KEYCLOAK_URL'], app.config['KEYCLOAK_REALM'])

    payload = {
        'client_id': request.json['clientId'],
        'client_secret': app.config['OAUTH2_CLIENT_SECRET'],
        'redirect_uri': request.json['redirectUri'],
        'grant_type': 'authorization_code',
        'code': request.json['code'],
    }

    try:
        r = requests.post(access_token_url, data=payload)
    except Exception:
        return jsonify(status="error", message="Failed to call Keycloak API over HTTPS")
    access_token = r.json()

    headers = {"Authorization": "{0} {1}".format(access_token['token_type'], access_token['access_token'])}
    r = requests.get("{0}/auth/realms/{1}/protocol/openid-connect/userinfo".format(app.config['KEYCLOAK_URL'], app.config['KEYCLOAK_REALM']), headers=headers)
    profile = r.json()

    roles = profile['roles']
    login = profile['preferred_username']

    if app.config['AUTH_REQUIRED'] and not ('*' in app.config['ALLOWED_KEYCLOAK_ROLES']
            or set(app.config['ALLOWED_KEYCLOAK_ROLES']).intersection(set(roles))):
        return jsonify(status="error", message="User %s is not authorized" % login), 403

    if app.config['CUSTOMER_VIEWS']:
        try:
            customer = customer_match(login, roles)
        except NoCustomerMatch:
            return jsonify(status="error", message="No customer lookup defined for user %s" % login), 403
    else:
        customer = None

    token = create_token(profile['sub'], profile['name'], login, provider='keycloak', customer=customer, scopes=scopes(login, groups=roles))
    return jsonify(token=token)


if 'SAML2_CONFIG' in app.config:
    spConfig = saml2.config.Config()
    saml2_config_default = {
        'entityid': absolute_url(),
        'service': {
            'sp': {
                'endpoints': {
                    'assertion_consumer_service': [
                        (absolute_url('/auth/saml'), saml2.BINDING_HTTP_POST)
                    ]
                }
            }
        }
    }
    spConfig.load(deepmerge(saml2_config_default, app.config['SAML2_CONFIG']))
    saml_client = saml2.client.Saml2Client(config=spConfig)


@app.route('/auth/saml', methods=['GET'])
def saml_redirect_to_idp():
    relay_state = None if request.args.get('usePostMessage') is None else 'usePostMessage'
    (session_id, result) = saml_client.prepare_for_authenticate(relay_state=relay_state)
    return make_response('', 302, result['headers'])


@app.route('/auth/saml', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def saml_response_from_idp():
    def _make_response(resp_obj, resp_code):
        if 'usePostMessage' in request.form.get('RelayState', '') and 'text/html' in request.headers.get('Accept', ''):
            origins = app.config.get('CORS_ORIGINS', [])
            response = make_response(
                '''<!DOCTYPE html>
                    <html lang="en">
                        <head>
                            <meta charset="UTF-8">
                            <title>Authenticating...</title>
                            <script type="application/javascript">
                                var origins = {origins};
                                // in case when API and WebUI are on the same origin
                                if (origins.indexOf(window.location.origin) < 0)
                                    origins.push(window.location.origin);
                                // only one will succeed
                                origins.forEach(origin => window.opener.postMessage({msg_data}, origin));
                                window.close();
                            </script>
                        </head>
                        <body></body>
                    </html>'''.format(msg_data=json.dumps(resp_obj), origins=json.dumps(origins)),
                resp_code
            )
            response.headers['Content-Type'] = 'text/html'
            return response
        else:
            return jsonify(**resp_obj), resp_code

    authn_response = saml_client.parse_authn_request_response(
        request.form['SAMLResponse'],
        saml2.entity.BINDING_HTTP_POST
    )
    identity = authn_response.get_identity()
    email = identity['emailAddress'][0]
    name = (app.config.get('SAML2_USER_NAME_FORMAT', '{givenName} {surname}')).format(**dict(map(lambda x: (x[0], x[1][0]), identity.items())))

    groups = identity.get('groups', [])
    if app.config['AUTH_REQUIRED'] and not ('*' in app.config['ALLOWED_SAML2_GROUPS']
            or set(app.config['ALLOWED_SAML2_GROUPS']).intersection(set(groups))):
        return _make_response({'status': 'error', 'message': 'User {} is not authorized'.format(email)}, 403)

    if app.config['CUSTOMER_VIEWS']:
        try:
            customer = customer_match(email, groups=[email.split('@')[1]])
        except NoCustomerMatch:
            return _make_response(
                {'status': 'error', 'message': 'No customer lookup defined for user %s' % email},
                403
            )
    else:
        customer = None

    token = create_token(email, name, email, provider='saml2', customer=customer, scopes=scopes(email, groups=groups))
    return _make_response({'status': 'ok', 'token': token}, 200)


@app.route('/auth/saml/metadata.xml', methods=['GET'])
def saml_metadata():
    edesc = saml2.metadata.entity_descriptor(spConfig)
    response = make_response(str(edesc))
    response.headers['Content-Type'] = 'text/xml; charset=utf-8'
    return response


@app.route('/userinfo', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission('read:userinfo')
def userinfo():

    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    return jsonify(parse_token(token))
