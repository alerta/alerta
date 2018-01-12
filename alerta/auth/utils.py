
import re
from datetime import datetime, timedelta
from functools import wraps
from uuid import uuid4

from flask import request, g, current_app
from jwt import DecodeError, ExpiredSignature, InvalidAudience
from six import text_type

from alerta.exceptions import ApiError, NoCustomerMatch
from alerta.models.customer import Customer
from alerta.models.key import ApiKey
from alerta.models.permission import Permission
from alerta.models.token import Jwt


try:
    import bcrypt

    def generate_password_hash(password):
        if isinstance(password, text_type):
            password = password.encode('utf-8')
        return bcrypt.hashpw(password, bcrypt.gensalt(prefix=b'2a')).decode('utf-8')

    def check_password_hash(pwhash, password):
        return bcrypt.checkpw(password.encode('utf-8'), pwhash.encode('utf-8'))

except ImportError:  # Google App Engine
    from werkzeug.security import generate_password_hash, check_password_hash


def is_authorized(allowed_setting, groups):
    return (current_app.config['AUTH_REQUIRED']
            and not ('*' in current_app.config[allowed_setting]
                     or set(current_app.config[allowed_setting]).intersection(set(groups))))


def get_customer(login, groups):
    if current_app.config['CUSTOMER_VIEWS']:
        try:
            return Customer.lookup(login, groups)
        except NoCustomerMatch as e:
            raise ApiError(str(e), 403)
    else:
        return


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
        preferred_username=login,
        orgs=orgs,
        roles=roles,
        groups=groups,
        provider=provider,
        scopes=scopes,
        email=email,
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
                g.user = jwt.preferred_username
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

            # Google App Engine Cron Service
            if request.headers.get('X-Appengine-Cron', False) and request.headers.get('X-Forwarded-For', '') == '0.1.0.1':
                return f(*args, **kwargs)

            raise ApiError('Missing authorization API Key or Bearer Token', 401)

        return wrapped
    return decorated
