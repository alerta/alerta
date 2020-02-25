import base64
import re
from functools import wraps
from typing import TYPE_CHECKING

import mohawk
from flask import current_app, g, request
from jwt import DecodeError, ExpiredSignature, InvalidAudience

from alerta.auth.hmac import HmacAuth
from alerta.auth.utils import get_customers, not_authorized
from alerta.exceptions import ApiError, BasicAuthError
from alerta.models.enums import ADMIN_SCOPES
from alerta.models.key import ApiKey
from alerta.models.permission import Permission
from alerta.models.token import Jwt
from alerta.models.user import User

if TYPE_CHECKING:
    from typing import List   # noqa
    from alerta.models.enums import Scope  # noqa


def permission(scope=None):
    def decorated(f):
        @wraps(f)
        def wrapped(*args, **kwargs):

            # API Key (Authorization: Key <key>)
            if 'Authorization' in request.headers and request.headers['Authorization'].startswith('Key '):
                auth_header = request.headers['Authorization']
                m = re.match(r'Key (\S+)', auth_header)
                key = m.group(1) if m else None
            # API Key (X-API-Key: <key>)
            elif 'X-API-Key' in request.headers:
                key = request.headers['X-API-Key']
            # API Key (/foo?api-key=<key>)
            else:
                key = request.args.get('api-key', None)

            if key:
                key_info = ApiKey.verify_key(key)
                if not key_info:
                    raise ApiError("API key parameter '%s' is invalid" % key, 401)
                g.user_id = None
                g.login = key_info.user
                g.customers = [key_info.customer] if key_info.customer else []
                g.scopes = key_info.scopes  # type: List[Scope]

                if not Permission.is_in_scope(scope, have_scopes=g.scopes):
                    raise ApiError('Missing required scope: %s' % scope.value, 403)
                else:
                    return f(*args, **kwargs)

            # Hawk HMAC Signature (Authorization: Hawk mac=...)
            if request.headers.get('Authorization', '').startswith('Hawk'):
                try:
                    receiver = HmacAuth.authenticate(request)
                except mohawk.exc.HawkFail as e:
                    raise ApiError(str(e), 401)

                g.user_id = None
                g.login = receiver.parsed_header.get('id')
                g.customers = []
                g.scopes = ADMIN_SCOPES

            # Bearer Token
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
                g.user_id = jwt.subject
                g.login = jwt.preferred_username
                g.customers = jwt.customers
                g.scopes = jwt.scopes  # type: List[Scope]

                if not Permission.is_in_scope(scope, have_scopes=g.scopes):
                    raise ApiError('Missing required scope: %s' % scope.value, 403)
                else:
                    return f(*args, **kwargs)

            # Basic Auth
            auth_header = request.headers.get('Authorization', '')
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

                g.user_id = user.id
                g.login = user.email
                g.customers = get_customers(user.email, groups=[user.domain])
                g.scopes = Permission.lookup(user.email, roles=user.roles)  # type: List[Scope]

                if not Permission.is_in_scope(scope, have_scopes=g.scopes):
                    raise BasicAuthError('Missing required scope: %s' % scope.value, 403)
                else:
                    return f(*args, **kwargs)

            if not current_app.config['AUTH_REQUIRED']:
                g.user_id = None
                g.login = None
                g.customers = []
                g.scopes = []  # type: List[Scope]
                return f(*args, **kwargs)

            # Google App Engine Cron Service
            if request.headers.get('X-Appengine-Cron', False) and request.headers.get('X-Forwarded-For', '') == '0.1.0.1':
                return f(*args, **kwargs)

            raise ApiError('Missing authorization API Key or Bearer Token', 401)

        return wrapped
    return decorated
