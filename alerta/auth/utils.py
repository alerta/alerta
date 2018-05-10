
import re
import logging

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
from alerta.utils.api import absolute_url

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
                g.customers = [key.customer] if key.customer else []
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
                g.customers = jwt.customers
                g.scopes = jwt.scopes

                if not Permission.is_in_scope(scope, g.scopes):
                    raise ApiError("Missing required scope: %s" % scope, 403)
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


try:
    import smtplib
    import socket
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
except ImportError:
    pass


def send_confirmation(user, hash):

    smtp_host = current_app.config['SMTP_HOST']
    smtp_port = current_app.config['SMTP_PORT']
    mail_localhost = current_app.config['MAIL_LOCALHOST']
    ssl_key_file = current_app.config['SSL_KEY_FILE']
    ssl_cert_file = current_app.config['SSL_CERT_FILE']

    mail_from = current_app.config['MAIL_FROM']
    smtp_username = current_app.config.get('SMTP_USERNAME', mail_from)
    smtp_password = current_app.config['SMTP_PASSWORD']

    msg = MIMEMultipart('related')
    msg['Subject'] = "[Alerta] Please verify your email '%s'" % user.email
    msg['From'] = mail_from
    msg['To'] = user.email
    msg.preamble = "[Alerta] Please verify your email '%s'" % user.email

    text = 'Hello {name}!\n\n' \
           'Please verify your email address is {email} by clicking on the link below:\n\n' \
           '{url}\n\n' \
           'You\'re receiving this email because you recently created a new Alerta account.' \
           ' If this wasn\'t you, please ignore this email.'.format(
               name=user.name, email=user.email, url=absolute_url('/auth/confirm/' + hash)
           )

    msg_text = MIMEText(text, 'plain', 'utf-8')
    msg.attach(msg_text)

    try:
        if current_app.config['SMTP_USE_SSL']:
            mx = smtplib.SMTP_SSL(smtp_host, smtp_port, local_hostname=mail_localhost, keyfile=ssl_key_file, certfile=ssl_cert_file)
        else:
            mx = smtplib.SMTP(smtp_host, smtp_port, local_hostname=mail_localhost)

        if current_app.config['DEBUG']:
            mx.set_debuglevel(True)

        mx.ehlo()

        if current_app.config['SMTP_STARTTLS']:
            mx.starttls()

        if smtp_password:
            mx.login(smtp_username, smtp_password)

        mx.sendmail(mail_from, [user.email], msg.as_string())
        mx.close()
    except smtplib.SMTPException as e:
        logging.error('Failed to send email : %s', str(e))
    except (socket.error, socket.herror, socket.gaierror) as e:
        logging.error('Mail server connection error: %s', str(e))
        return
    except Exception as e:
        logging.error('Unhandled exception: %s', str(e))
