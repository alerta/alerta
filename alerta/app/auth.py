
import jwt
import json
import requests
import bcrypt

from datetime import datetime, timedelta
from functools import wraps
from flask import g, request, redirect
from flask.ext.cors import cross_origin
from jwt import DecodeError, ExpiredSignature, InvalidAudience
from base64 import urlsafe_b64decode
from urlparse import parse_qsl
from urllib import urlencode
from requests_oauthlib import OAuth1
from uuid import uuid4

from alerta.app import app, db
from alerta.app.utils import jsonify, jsonp, DateEncoder

BASIC_AUTH_REALM = "Alerta"


class AuthError(Exception):
    pass


class Forbidden(Exception):
    pass


def verify_api_key(key, method):
    perm = db.is_key_valid(key)
    if not perm:
        raise AuthError("API key '%s' is invalid" % key)
    if method in ['POST', 'DELETE'] and perm != 'read-write':
        raise Forbidden("%s method requires 'read-write' API Key" % method)
    db.update_key(key)


def create_token(user, name, login, provider=None):
    payload = {
        'iss': "%s" % request.host_url,
        'sub': user,
        'iat': datetime.utcnow(),
        'aud': app.config['OAUTH2_CLIENT_ID'],
        'exp': datetime.utcnow() + timedelta(days=14),
        'name': name,
        'login': login,
        'provider': provider
    }
    token = jwt.encode(payload, key=app.config['SECRET_KEY'], json_encoder=DateEncoder)
    return token.decode('unicode_escape')


def parse_token(token):
    return jwt.decode(token, key=app.config['SECRET_KEY'], audience=app.config['OAUTH2_CLIENT_ID'])


def authenticate(message, status_code=401):
    return jsonify(status="error", message=message), status_code


def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):

        if not app.config['AUTH_REQUIRED']:
            return f(*args, **kwargs)

        if 'api-key' in request.args:
            key = request.args['api-key']
            try:
                verify_api_key(key, request.method)
            except AuthError as e:
                return authenticate(str(e), 401)
            except Forbidden as e:
                return authenticate(str(e), 403)
            except Exception as e:
                return authenticate(str(e), 500)
            return f(*args, **kwargs)

        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return authenticate('Missing authorization API Key or Bearer Token')

        if auth_header.startswith('Key'):
            key = auth_header.replace('Key ', '')
            try:
                verify_api_key(key, request.method)
            except AuthError as e:
                return authenticate(str(e), 401)
            except Forbidden as e:
                return authenticate(str(e), 403)
            except Exception as e:
                return authenticate(str(e), 500)
            return f(*args, **kwargs)

        if auth_header.startswith('Bearer'):
            token = auth_header.replace('Bearer ', '')
            try:
                payload = parse_token(token)
            except DecodeError:
                return authenticate('Token is invalid')
            except ExpiredSignature:
                return authenticate('Token has expired')
            except InvalidAudience:
                return authenticate('Invalid audience')
            g.user_id = payload['sub']
            return f(*args, **kwargs)

        return authenticate('Authentication required')

    return decorated


@app.route('/auth/login', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def login():
    try:
        email = request.json['email']
        password = request.json['password']
    except KeyError:
        return jsonify(status="error", message="Must supply email address and password"), 401, \
            {'WWW-Authenticate': 'Basic realm="%s"' % BASIC_AUTH_REALM}

    if app.config['AUTH_REQUIRED'] and not db.is_user_valid(login=email):
        return jsonify(status="error", message="User %s is not authorized" % email), 401, \
            {'WWW-Authenticate': 'Basic realm="%s"' % BASIC_AUTH_REALM}
    elif not db.is_user_valid(login=email):
        return jsonify(status="error", message="User %s does not exist" % email), 401, \
            {'WWW-Authenticate': 'Basic realm="%s"' % BASIC_AUTH_REALM}
    else:
        user = db.get_users(query={"login": email})[0]

    if not bcrypt.hashpw(password.encode('utf-8'), user['password'].encode('utf-8')) == user['password'].encode('utf-8'):
        return jsonify(status="error", message="User %s is not authorized" % email), 401, \
            {'WWW-Authenticate': 'Basic realm="%s"' % BASIC_AUTH_REALM}

    token = create_token(user['id'], user['name'], email, provider='basic')
    return jsonify(token=token)


@app.route('/auth/signup', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def signup():

    if request.json and 'name' in request.json:
        name = request.json["name"]
        login = request.json["email"]
        password = request.json["password"]
        provider = request.json.get("provider", "basic")
        text = request.json.get("text", "")
        try:
            user_id = db.save_user(str(uuid4()), name, login, password, provider, text)
        except Exception as e:
            return jsonify(status="error", message=str(e)), 500
    else:
        return jsonify(status="error", message="must supply user 'name', 'email' and 'password' as parameters"), 400

    if user_id:
        user = db.get_user(user_id)
    else:
        user = db.get_users(query={"login": login})[0]

    token = create_token(user['id'], user['name'], login, provider='basic')
    return jsonify(token=token)


@app.route('/auth/google', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def google():
    access_token_url = 'https://accounts.google.com/o/oauth2/token'
    people_api_url = 'https://www.googleapis.com/plus/v1/people/me/openIdConnect'

    payload = dict(client_id=request.json['clientId'],
                   redirect_uri=request.json['redirectUri'],
                   client_secret=app.config['OAUTH2_CLIENT_SECRET'],
                   code=request.json['code'],
                   grant_type='authorization_code')

    try:
        r = requests.post(access_token_url, data=payload)
    except Exception:
        return jsonify(status="error", message="Failed to call Google API over HTTPS")
    token = json.loads(r.text)

    if 'id_token' not in token:
        return jsonify(status="error", message=token.get('error', "Invalid token"))

    id_token = token['id_token'].split('.')[1].encode('ascii', 'ignore')
    id_token += '=' * (4 - (len(id_token) % 4))
    claims = json.loads(urlsafe_b64decode(id_token))

    if claims.get('aud') != app.config['OAUTH2_CLIENT_ID']:
        return jsonify(status="error", message="Token client audience is invalid"), 400

    email = claims.get('email')
    if app.config['AUTH_REQUIRED'] and not ('*' in app.config['ALLOWED_EMAIL_DOMAINS']
            or email.split('@')[1] in app.config['ALLOWED_EMAIL_DOMAINS']
            or db.is_user_valid(login=email)):
        return jsonify(status="error", message="User %s is not authorized" % email), 403

    headers = {'Authorization': 'Bearer ' + token['access_token']}
    r = requests.get(people_api_url, headers=headers)
    profile = json.loads(r.text)

    try:
        token = create_token(profile['sub'], profile['name'], email, provider='google')
    except KeyError:
        return jsonify(status="error", message="Google+ API is not enabled for this Client ID")

    return jsonify(token=token)

@app.route('/auth/github', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def github():
    access_token_url = 'https://github.com/login/oauth/access_token'
    users_api_url = 'https://api.github.com/user'

    params = {
        'client_id': request.json['clientId'],
        'redirect_uri': request.json['redirectUri'],
        'client_secret': app.config['OAUTH2_CLIENT_SECRET'],
        'code': request.json['code']
    }

    r = requests.get(access_token_url, params=params)
    access_token = dict(parse_qsl(r.text))

    r = requests.get(users_api_url, params=access_token)
    profile = json.loads(r.text)

    r = requests.get(profile['organizations_url'], params=access_token)
    organizations = [o['login'] for o in json.loads(r.text)]

    login = profile['login']
    if app.config['AUTH_REQUIRED'] and not ('*' in app.config['ALLOWED_GITHUB_ORGS']
            or set(app.config['ALLOWED_GITHUB_ORGS']).intersection(set(organizations))
            or db.is_user_valid(login=login)):
        return jsonify(status="error", message="User %s is not authorized" % profile['login']), 403

    token = create_token(profile['id'], profile.get('name', None) or '@'+login, login, provider='github')
    return jsonify(token=token)

@app.route('/auth/twitter')
@cross_origin(supports_credentials=True)
def twitter():
    request_token_url = 'https://api.twitter.com/oauth/request_token'
    access_token_url = 'https://api.twitter.com/oauth/access_token'
    authenticate_url = 'https://api.twitter.com/oauth/authenticate'

    if request.args.get('oauth_token') and request.args.get('oauth_verifier'):
        auth = OAuth1(app.config['OAUTH2_CLIENT_ID'],
                      client_secret=app.config['OAUTH2_CLIENT_SECRET'],
                      resource_owner_key=request.args.get('oauth_token'),
                      verifier=request.args.get('oauth_verifier'))
        r = requests.post(access_token_url, auth=auth)
        profile = dict(parse_qsl(r.text))

        login = profile['screen_name']
        if app.config['AUTH_REQUIRED'] and not db.is_user_valid(login=login):
            return jsonify(status="error", message="User %s is not authorized" % login), 403

        token = create_token(profile['user_id'], '@'+login, login, provider='twitter')
        return jsonify(token=token)
    else:
        oauth = OAuth1(app.config['OAUTH2_CLIENT_ID'],
                       client_secret=app.config['OAUTH2_CLIENT_SECRET'],
                       callback_uri=app.config.get('TWITTER_CALLBACK_URL', request.headers.get('Referer', ''))
        )
        r = requests.post(request_token_url, auth=oauth)
        oauth_token = dict(parse_qsl(r.text))
        qs = urlencode(dict(oauth_token=oauth_token['oauth_token']))
        return redirect(authenticate_url + '?' + qs)
