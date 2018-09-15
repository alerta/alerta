from datetime import datetime, timedelta
from urllib.parse import urljoin
from uuid import uuid4

from flask import current_app, request
from itsdangerous import BadData, SignatureExpired, URLSafeTimedSerializer
from six import text_type

from alerta.app import mailer
from alerta.exceptions import ApiError, NoCustomerMatch
from alerta.models.customer import Customer
from alerta.models.permission import Permission
from alerta.models.token import Jwt

try:
    import bcrypt  # type: ignore

    def generate_password_hash(password):
        if isinstance(password, text_type):
            password = password.encode('utf-8')
        return bcrypt.hashpw(password, bcrypt.gensalt(prefix=b'2a')).decode('utf-8')

    def check_password_hash(pwhash, password):
        return bcrypt.checkpw(password.encode('utf-8'), pwhash.encode('utf-8'))

except ImportError:  # Google App Engine
    from werkzeug.security import generate_password_hash, check_password_hash  # noqa


def not_authorized(allowed_setting, groups):
    return (current_app.config['AUTH_REQUIRED'] and
            not ('*' in current_app.config[allowed_setting] or
                 set(current_app.config[allowed_setting]).intersection(set(groups))))


def get_customers(login, groups):
    if current_app.config['CUSTOMER_VIEWS']:
        try:
            return Customer.lookup(login, groups)
        except NoCustomerMatch as e:
            raise ApiError(str(e), 403)
    else:
        return


def create_token(user_id, name, login, provider, customers, orgs=None, groups=None, roles=None, email=None, email_verified=None):
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
        customers=customers
    )


def send_confirmation(user):
    token = generate_email_token(email=user.email, salt='confirm')
    user.set_email_hash(token)

    ui_base_url = request.referrer
    print(ui_base_url)

    subject = "[Alerta] Please verify your email '%s'" % user.email
    text = 'Hello {name}!\n\n' \
           'Please verify your email address is {email} by clicking on the link below:\n\n' \
           '{url}\n\n' \
           'You\'re receiving this email because you recently created a new Alerta account.' \
           ' If this wasn\'t you, please ignore this email.'.format(
               name=user.name, email=user.email, url=urljoin(request.referrer, '/#/confirm/' + token)
           )
    mailer.send_email(user.email, subject, body=text)


def send_password_reset(user):
    token = generate_email_token(email=user.email, salt='reset')
    user.set_email_hash(token)

    subject = '[Alerta] Reset password request'
    text = 'You forgot your password. Reset it by clicking on the link below:\n\n' \
           '{url}\n\n' \
           'You\'re receiving this email because you asked for a password reset of an Alerta account.' \
           ' If this wasn\'t you, please ignore this email.'.format(
               name=user.name, email=user.email, url=urljoin(request.referrer, '/#/reset/' + token)
           )
    mailer.send_email(user.email, subject, body=text)


def generate_email_token(email, salt):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt)


def confirm_email_token(token, salt, expiration=900):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(
            token,
            salt=salt,
            max_age=expiration
        )
    except SignatureExpired as e:
        raise ApiError('confirmation token signature has expired', 401, errors=[str(e)])
    except BadData as e:
        raise ApiError('confirmation token invalid', 400, errors=[str(e)])

    return email
