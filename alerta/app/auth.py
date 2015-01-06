
import jwt
import json
import requests

from datetime import datetime, timedelta
from functools import wraps
from flask import g, request, jsonify
from jwt import DecodeError, ExpiredSignature

from alerta.app import app, db
from alerta.app.utils import crossdomain, DateEncoder


def verify_api_key(key):
    if not db.is_key_valid(key):
        return False
    db.update_key(key)
    return True


def create_token(user):
    payload = {
        'sub': user,
        # 'sub': user.id,
        'iat': datetime.now(),
        'exp': datetime.now() + timedelta(days=14)
    }
    token = jwt.encode(payload, app.config['SECRET_KEY'], json_encoder=DateEncoder)
    return token.decode('unicode_escape')


def parse_token(req):
    token = req.headers.get('Authorization').split()[1]
    return jwt.decode(token, app.config['SECRET_KEY'])


def authenticate(message):
    return jsonify(status="error", message=message), 401


def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

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

        try:
            payload = parse_token(request)
        except DecodeError:
            return authenticate('Token is invalid')
        except ExpiredSignature:
            return authenticate('Token has expired')

        print payload

        g.user_id = payload['sub']

        return f(*args, **kwargs)
    return decorated_function


# @app.route('/auth/github', methods=['POST'])
# def github():
#     access_token_url = 'https://github.com/login/oauth/access_token'
#     users_api_url = 'https://api.github.com/user'
#
#     params = {
#         'client_id': request.json['clientId'],
#         'redirect_uri': request.json['redirectUri'],
#         'client_secret': app.config['GITHUB_SECRET'],
#         'code': request.json['code']
#     }
#
#     # Step 1. Exchange authorization code for access token.
#     r = requests.get(access_token_url, params=params)
#     access_token = dict(parse_qsl(r.text))
#     headers = {'User-Agent': 'Satellizer'}
#
#     # Step 2. Retrieve information about the current user.
#     r = requests.get(users_api_url, params=access_token, headers=headers)
#     profile = json.loads(r.text)
#
#     # Step 3. (optional) Link accounts.
#     if request.headers.get('Authorization'):
#         user = User.query.filter_by(facebook=profile['id']).first()
#         if user:
#             response = jsonify(message='There is already a GitHub account that belongs to you')
#             response.status_code = 409
#             return response
#
#         payload = parse_token(request)
#
#         user = User.query.filter_by(id=payload['sub']).first()
#         if not user:
#             response = jsonify(message='User not found')
#             response.status_code = 400
#             return response
#
#         u = User(github=profile['id'], display_name=profile['name'])
#         db.session.add(u)
#         db.session.commit()
#         token = create_token(u)
#         return jsonify(token=token)
#
#     # Step 4. Create a new account or return an existing one.
#     user = User.query.filter_by(github=profile['id']).first()
#     if user:
#         token = create_token(user)
#         return jsonify(token=token)
#
#     u = User(github=profile['id'], display_name=profile['name'])
#     db.session.add(u)
#     db.session.commit()
#     token = create_token(u)
#     return jsonify(token=token)


@app.route('/auth/google', methods=['OPTIONS', 'POST'])
@crossdomain(origin='http://localhost', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept', 'Authorization'])
def google():
    access_token_url = 'https://accounts.google.com/o/oauth2/token'
    people_api_url = 'https://www.googleapis.com/plus/v1/people/me/openIdConnect'

    payload = dict(client_id=request.json['clientId'],
                   redirect_uri=request.json['redirectUri'],
                   client_secret=app.config['GOOGLE_SECRET'],
                   code=request.json['code'],
                   grant_type='authorization_code')

    r = requests.post(access_token_url, data=payload)
    token = json.loads(r.text)

    # verify id_token aud = client id
    print token['id_token']

    headers = {'Authorization': 'Bearer ' + token['access_token']}

    r = requests.get(people_api_url, headers=headers)
    profile = json.loads(r.text)

    # verify email domain in ALLOWED_EMAIL_DOMAINS

    user = db.get_user(profile['sub'])
    if user:
        token = create_token(user)
        return jsonify(token=token)

    db.save_user(profile['sub'], name=profile['name'], email=profile['email'], provider='google')
    token = create_token(profile['name'])
    return jsonify(token=token)


# @app.route('/auth/twitter')
# def twitter():
#     request_token_url = 'https://api.twitter.com/oauth/request_token'
#     access_token_url = 'https://api.twitter.com/oauth/access_token'
#     authenticate_url = 'https://api.twitter.com/oauth/authenticate'
#
#     if request.args.get('oauth_token') and request.args.get('oauth_verifier'):
#         auth = OAuth1(app.config['TWITTER_CONSUMER_KEY'],
#                       client_secret=app.config['TWITTER_CONSUMER_SECRET'],
#                       resource_owner_key=request.args.get('oauth_token'),
#                       verifier=request.args.get('oauth_verifier'))
#         r = requests.post(access_token_url, auth=auth)
#         profile = dict(parse_qsl(r.text))
#
#         user = User.query.filter_by(twitter=profile['user_id']).first()
#         if user:
#             token = create_token(user)
#             return jsonify(token=token)
#         u = User(twitter=profile['user_id'],
#                  display_name=profile['screen_name'])
#         db.session.add(u)
#         db.session.commit()
#         token = create_token(u)
#         return jsonify(token=token)
#     else:
#         oauth = OAuth1(app.config['TWITTER_CONSUMER_KEY'],
#                        client_secret=app.config['TWITTER_CONSUMER_SECRET'],
#                        callback_uri=app.config['TWITTER_CALLBACK_URL'])
#         r = requests.post(request_token_url, auth=oauth)
#         oauth_token = dict(parse_qsl(r.text))
#         qs = urlencode(dict(oauth_token=oauth_token['oauth_token']))
#         return redirect(authenticate_url + '?' + qs)
#
