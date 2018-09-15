import base64
import re
from functools import wraps

from flask import current_app, g, request
from jwt import DecodeError, ExpiredSignature, InvalidAudience

from alerta.auth.utils import get_customers, not_authorized
from alerta.exceptions import ApiError, BasicAuthError
from alerta.models.key import ApiKey
from alerta.models.permission import Permission
from alerta.models.token import Jwt
from alerta.models.user import User


def permission(scope):
    def decorated(f):
        @wraps(f)
        def wrapped(*args, **kwargs):

            auth_header = request.headers.get('Authorization', '')

            # API Key
            m = re.match(r'Key (\S+)', auth_header)
            param = m.group(1) if m else request.args.get('api-key', None)

            if param:
                key = ApiKey.verify_key(param)
                if not key:
                    raise ApiError("API key parameter '%s' is invalid" % param, 401)
                g.user = key.user
                g.customers = [key.customer] if key.customer else []
                g.scopes = key.scopes

                if not Permission.is_in_scope(scope, g.scopes):
                    raise ApiError('Missing required scope: %s' % scope, 403)
                else:
                    return f(*args, **kwargs)

            # Bearer Token
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
                g.customers = jwt.customers
                g.scopes = jwt.scopes

                if not Permission.is_in_scope(scope, g.scopes):
                    raise ApiError('Missing required scope: %s' % scope, 403)
                else:
                    return f(*args, **kwargs)

            # Basic Auth
            m = re.match(r'Basic (\S+)', auth_header)
            credentials = m.group(1) if m else None

            if credentials:
                try:
                    username, password = base64.b64decode(credentials).decode('utf-8').split(':')
                except Exception as e:
                    raise BasicAuthError('Invalid credentials', 400, errors=[str(e)])

                user = User.check_credentials(username, password)
                if not user:
                    raise BasicAuthError('Authorization required', 401)

                if current_app.config['EMAIL_VERIFICATION'] and not user.email_verified:
                    raise BasicAuthError('email not verified', 401)

                if not_authorized('ALLOWED_EMAIL_DOMAINS', groups=[user.domain]):
                    raise BasicAuthError('Unauthorized domain', 403)

                g.user = user.email
                g.customers = get_customers(user.email, groups=[user.domain])
                g.scopes = Permission.lookup(user.email, groups=user.roles)

                if not Permission.is_in_scope(scope, g.scopes):
                    raise BasicAuthError('Missing required scope: %s' % scope, 403)
                else:
                    return f(*args, **kwargs)

            if not current_app.config['AUTH_REQUIRED']:
                g.user = None
                g.customers = []
                g.scopes = []
                return f(*args, **kwargs)

            # Google App Engine Cron Service
            if request.headers.get('X-Appengine-Cron', False) and request.headers.get('X-Forwarded-For', '') == '0.1.0.1':
                return f(*args, **kwargs)

            raise ApiError('Missing authorization API Key or Bearer Token', 401)

        return wrapped
    return decorated
