import logging
from datetime import datetime, timedelta
from flask import request, current_app
from six import text_type
from uuid import uuid4

from alerta.exceptions import ApiError, NoCustomerMatch
from alerta.models.customer import Customer
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
