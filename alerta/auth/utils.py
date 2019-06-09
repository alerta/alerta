from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, cast
from urllib.parse import urljoin
from uuid import uuid4

from flask import current_app, request
from itsdangerous import BadData, SignatureExpired, URLSafeTimedSerializer
from six import text_type

from alerta.app import mailer
from alerta.exceptions import ApiError, NoCustomerMatch
from alerta.models.customer import Customer
from alerta.models.token import Jwt
from alerta.utils.response import absolute_url

if TYPE_CHECKING:
    from alerta.models.user import User  # noqa

try:
    import bcrypt  # type: ignore

    def generate_password_hash(password: Any) -> str:
        if isinstance(password, text_type):
            password = password.encode('utf-8')
        return bcrypt.hashpw(password, bcrypt.gensalt(prefix=b'2a')).decode('utf-8')

    def check_password_hash(pwhash: str, password: Any) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), pwhash.encode('utf-8'))

except ImportError:  # Google App Engine
    from werkzeug.security import generate_password_hash, check_password_hash  # noqa


def not_authorized(allowed_setting: str, groups: List[str]) -> bool:
    return (current_app.config['AUTH_REQUIRED'] and
            not ('*' in current_app.config[allowed_setting] or
                 set(current_app.config[allowed_setting]).intersection(set(groups))))


def get_customers(login: str, groups: List[str]) -> List[str]:
    if current_app.config['CUSTOMER_VIEWS']:
        try:
            return Customer.lookup(login, groups)
        except NoCustomerMatch as e:
            raise ApiError(str(e), 403)
    else:
        return []


def create_token(user_id: str, name: str, login: str, provider: str, customers: List[str], scopes: List[str],
                 email: str=None, email_verified: bool=None, picture: str=None, **kwargs) -> 'Jwt':
    now = datetime.utcnow()
    return Jwt(
        iss=request.url_root,
        typ='Bearer',
        sub=user_id,
        aud=current_app.config.get('OAUTH2_CLIENT_ID') or current_app.config.get('SAML2_ENTITY_ID') or absolute_url(),
        exp=(now + timedelta(days=current_app.config['TOKEN_EXPIRE_DAYS'])),
        nbf=now,
        iat=now,
        jti=str(uuid4()),
        name=name,
        preferred_username=login,
        email=email,
        email_verified=email_verified,
        provider=provider,
        scopes=scopes,
        customers=customers,
        picture=picture,
        **kwargs
    )


def link(base_url, *parts):
    if base_url.endswith('/'):
        return urljoin(base_url, '/'.join(('#',) + parts))  # hashbang mode
    else:
        return urljoin(base_url, '/'.join(parts))  # html5 mode


def send_confirmation(user: 'User', token: str) -> None:
    subject = "[Alerta] Please verify your email '%s'" % user.email
    text = 'Hello {name}!\n\n' \
           'Please verify your email address is {email} by clicking on the link below:\n\n' \
           '{url}\n\n' \
           'You\'re receiving this email because you recently created a new Alerta account.' \
           ' If this wasn\'t you, please ignore this email.'.format(
               name=user.name, email=user.email, url=link(request.referrer, 'confirm', token)
           )
    mailer.send_email(user.email, subject, body=text)


def send_password_reset(user: 'User', token: str) -> None:
    subject = '[Alerta] Reset password request'
    text = 'You forgot your password. Reset it by clicking on the link below:\n\n' \
           '{url}\n\n' \
           'You\'re receiving this email because you asked for a password reset of an Alerta account.' \
           ' If this wasn\'t you, please ignore this email.'.format(
               name=user.name, email=user.email, url=link(request.referrer, 'reset', token)
           )
    mailer.send_email(user.email, subject, body=text)


def generate_email_token(email: str, salt: str=None) -> str:
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return cast(str, serializer.dumps(email, salt))


def confirm_email_token(token: str, salt: str=None, expiration: int=900) -> str:
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(
            token,
            salt=salt,
            max_age=expiration
        )
    except SignatureExpired as e:
        raise ApiError('confirmation token has expired', 401, errors=['invalid_token', str(e)])
    except BadData as e:
        raise ApiError('confirmation token invalid', 400, errors=['invalid_request', str(e)])

    return email
