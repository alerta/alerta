
import re

from uuid import uuid4
from datetime import datetime, timedelta
from functools import wraps
from jwt import DecodeError, ExpiredSignature, InvalidAudience

from flask import request, g, current_app

from alerta.app.models.key import ApiKey
from alerta.app.models.token import Jwt
from alerta.app.models.permission import Permission
from alerta.app.exceptions import ApiError


def is_authorized(allowed_setting, groups):
    return (current_app.config['AUTH_REQUIRED']
            and not ('*' in current_app.config[allowed_setting]
                     or set(current_app.config[allowed_setting]).intersection(set(groups))))


def create_token(user_id, name, login, provider, customer, orgs=None, groups=None, roles=None, email=None, email_verified=None):
    now = datetime.utcnow()
    scopes = Permission.lookup(login, groups=(roles or []) + (groups or []) + (orgs or []))
    return Jwt(
        iss=request.url_root,
        sub=user_id,
        aud=current_app.config.get('OAUTH2_CLIENT_ID', None) or request.url_root,
        exp=(now + timedelta(days=current_app.config['TOKEN_EXPIRE_DAYS'])),
        nbf=now,
        iat=now,
        jti=str(uuid4()),
        name=name,
        login=login,
        email=email,
        orgs=orgs,
        roles=roles,
        groups=groups,
        provider=provider,
        scopes=scopes,
        email_verified=email_verified,
        customer=customer
    )


def permission(scope):
    def decorated(f):
        @wraps(f)
        def wrapped(*args, **kwargs):

            auth_header = request.headers.get('Authorization', '')
            m = re.match(r'Key (\S+)', auth_header)
            param = m.group(1) if m else request.args.get('api-key', None)

            if param:
                key = ApiKey.verify_key(param)
                if not key:
                    raise ApiError("API key parameter '%s' is invalid" % param, 401)
                g.user = key.user
                g.customer = key.customer
                g.scopes = key.scopes

                if not Permission.is_in_scope(scope, g.scopes):
                    raise ApiError('Missing required scope: %s' % scope, 403)
                else:
                    return f(*args, **kwargs)

            auth_header = request.headers.get('Authorization', '')
            m = re.match(r'Bearer (\S+)', auth_header)
            token = m.group(1) if m else None

            if token:
                try:
                    jwt = Jwt.parse(token)
                except DecodeError:
                    raise ApiError('Token is invalid', 401)
                except ExpiredSignature:
                    raise ApiError('Token has expired', 401)
                except InvalidAudience:
                    raise ApiError('Invalid audience', 401)
                g.user = jwt.login
                g.customer = jwt.customer
                g.scopes = jwt.scopes

                if not Permission.is_in_scope(scope, g.scopes):
                    raise ApiError("Missing required scope: %s" % scope, 403)
                else:
                    return f(*args, **kwargs)

            if not current_app.config['AUTH_REQUIRED']:
                g.user = None
                g.customer = None
                g.scopes = []
                return f(*args, **kwargs)

            raise ApiError('Missing authorization API Key or Bearer Token', 401)

        return wrapped
    return decorated
