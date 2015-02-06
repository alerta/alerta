
import jwt
import json
import requests

from datetime import datetime, timedelta
from functools import wraps
from flask import g, request
from flask.ext.cors import cross_origin
from jwt import DecodeError, ExpiredSignature, InvalidAudience
from base64 import urlsafe_b64decode
from urlparse import parse_qsl

from alerta.app import app, db
from alerta.app.utils import jsonify, jsonp, DateEncoder


def verify_api_key(key):
    if not db.is_key_valid(key):
        return False
    db.update_key(key)
    return True


def create_token(user, name, email, provider=None):
    payload = {
        'iss': "%s" % request.host_url,
        'sub': user,
        'iat': datetime.now(),
        'aud': app.config['OAUTH2_CLIENT_ID'],
        'exp': datetime.now() + timedelta(days=14),
        'name': name,
        'email': email,
        'provider': provider
    }
    token = jwt.encode(payload, key=app.config['SECRET_KEY'], json_encoder=DateEncoder)
    return token.decode('unicode_escape')


def parse_token(token):
    return jwt.decode(token, key=app.config['SECRET_KEY'], audience=app.config['OAUTH2_CLIENT_ID'])


def authenticate(message):
    return jsonify(status="error", message=message), 401


def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):

        if not app.config['AUTH_REQUIRED']:
            return f(*args, **kwargs)

        if 'api-key' in request.args:
            key = request.args['api-key']
            if not verify_api_key(key):
                return authenticate('API key is invalid')
            return f(*args, **kwargs)

        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return authenticate('Missing authorization API Key or Bearer Token')

        if auth_header.startswith('Key'):
            key = auth_header.replace('Key ', '')
            if not verify_api_key(key):
                return authenticate('API key is invalid')
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

@app.route('/auth/google', methods=['OPTIONS', 'POST'])
@cross_origin()
@jsonp
def google():
    access_token_url = 'https://accounts.google.com/o/oauth2/token'
    people_api_url = 'https://www.googleapis.com/plus/v1/people/me/openIdConnect'

    payload = dict(client_id=request.json['clientId'],
                   redirect_uri=request.json['redirectUri'],
                   client_secret=app.config['OAUTH2_CLIENT_SECRET'],
                   code=request.json['code'],
                   grant_type='authorization_code')

    r = requests.post(access_token_url, data=payload)
    token = json.loads(r.text)

    if 'id_token' not in token:
        return jsonify(status="error", message=token.get('error', "Invalid token"))

    id_token = token['id_token'].split('.')[1].encode('ascii', 'ignore')
    id_token += '=' * (4 - (len(id_token) % 4))
    claims = json.loads(urlsafe_b64decode(id_token))

    if claims.get('aud') != app.config['OAUTH2_CLIENT_ID']:
        return jsonify(status="error", message="Token client audience is invalid"), 400

    email = claims.get('email')
    if not ('*' in app.config['ALLOWED_EMAIL_DOMAINS']
            or email.split('@')[1] in app.config['ALLOWED_EMAIL_DOMAINS']
            or db.is_user_valid(email)):
        return jsonify(status="error", message="User %s is not authorized" % email), 403

    headers = {'Authorization': 'Bearer ' + token['access_token']}
    r = requests.get(people_api_url, headers=headers)
    profile = json.loads(r.text)

    try:
        token = create_token(profile['sub'], profile['name'], profile['email'], provider='google')
    except KeyError:
        return jsonify(status="error", message="Google+ API is not enabled for this Client ID")

    return jsonify(token=token)

@app.route('/auth/github', methods=['OPTIONS', 'POST'])
@cross_origin()
@jsonp
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

    if not ('*' in app.config['ALLOWED_GITHUB_ORGS']
            or (set(app.config['ALLOWED_GITHUB_ORGS']).intersection(set(organizations)))):
        return jsonify(status="error", message="User %s is not authorized" % profile['login']), 403

    token = create_token(profile['login'], profile['name'], profile['email'], provider='github')

    return jsonify(token=token)
