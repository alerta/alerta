import base64
import re
from functools import wraps
from typing import TYPE_CHECKING

import mohawk
from flask import current_app, g, request
from jwt import DecodeError, ExpiredSignatureError, InvalidAudienceError

from alerta.auth.hmac import HmacAuth
from alerta.auth.utils import get_customers, not_authorized
from alerta.exceptions import ApiError, BasicAuthError
from alerta.models.enums import ADMIN_SCOPES
from alerta.models.key import ApiKey
from alerta.models.permission import Permission
from alerta.models.token import Jwt
from alerta.models.user import User

if TYPE_CHECKING:
    from typing import List  # noqa

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
                    raise ApiError(f"API key parameter '{key}' is invalid", 401)
                g.user_id = None
                g.login = key_info.user
                g.customers = [key_info.customer] if key_info.customer else []
                g.scopes = key_info.scopes  # type: List[Scope]

                if not Permission.is_in_scope(scope, have_scopes=g.scopes):
                    raise ApiError(f'Missing required scope: {scope}', 403)
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
                return f(*args, **kwargs)

            # Bearer Token
            auth_header = request.headers.get('Authorization', '')
            m = re.match(r'Bearer (\S+)', auth_header)
            token = m.group(1) if m else None

            if token:
                try:
                    jwt = Jwt.parse(token)
                except DecodeError:
                    raise ApiError('Token is invalid', 401)
                except ExpiredSignatureError:
                    raise ApiError('Token has expired', 401)
                except InvalidAudienceError:
                    raise ApiError('Invalid audience', 401)
                g.user_id = jwt.oid or jwt.subject
                g.login = jwt.preferred_username
                g.customers = jwt.customers
                g.scopes = jwt.scopes  # type: List[Scope]

                if not Permission.is_in_scope(scope, have_scopes=g.scopes):
                    raise ApiError(f'Missing required scope: {scope}', 403)
                else:
                    return f(*args, **kwargs)

            # AuthProxy
            proxy_user_header = current_app.config['AUTH_PROXY_USER_HEADER']
            proxy_roles_header = current_app.config['AUTH_PROXY_ROLES_HEADER']
            proxy_roles_header_sep = current_app.config['AUTH_PROXY_ROLES_SEPARATOR']

            if current_app.config['AUTH_PROXY'] and proxy_user_header in request.headers:
                username = request.headers[proxy_user_header]
                roles = request.headers.get(proxy_roles_header, '').split(proxy_roles_header_sep)

                user = User.find_by_username(username)

                if not user:
                    if current_app.config['AUTH_PROXY_AUTO_SIGNUP']:
                        try:
                            user = User(name=username, login=username, password='', email='', roles=roles, text='Proxy user')
                            user = user.create()
                        except Exception as e:
                            ApiError(str(e), 500)
                    else:
                        raise ApiError('user auto-signup is disabled', 403)

                g.user_id = user.id
                g.login = user.login
                g.customers = get_customers(user.login, groups=user.get_groups())
                g.scopes = Permission.lookup(user.login, roles=roles)  # type: List[Scope]

                if not Permission.is_in_scope(scope, have_scopes=g.scopes):
                    raise BasicAuthError(f'Missing required scope: {scope}', 403)
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
                    raise BasicAuthError(f'Missing required scope: {scope}', 403)
                else:
                    return f(*args, **kwargs)

            # auth not required
            if not current_app.config['AUTH_REQUIRED']:
                g.user_id = None
                g.login = None
                g.customers = []
                g.scopes = []  # type: List[Scope]
                return f(*args, **kwargs)

            # auth required for admin/write, but readonly is allowed
            if current_app.config['AUTH_REQUIRED'] and current_app.config['ALLOW_READONLY']:
                g.user_id = None
                g.login = None
                g.customers = []
                g.scopes = current_app.config['READONLY_SCOPES']
                return f(*args, **kwargs)

            # Google App Engine Cron Service
            if request.headers.get('X-Appengine-Cron', False) and request.headers.get('X-Forwarded-For', '') == '0.1.0.1':
                return f(*args, **kwargs)

            raise ApiError('Missing authorization API Key or Bearer Token', 401)

        return wrapped
    return decorated
