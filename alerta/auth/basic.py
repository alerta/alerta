
import logging
from uuid import uuid4

from flask import current_app, request, jsonify, render_template
from flask_cors import cross_origin

from alerta.auth.utils import is_authorized, create_token, get_customer
from alerta.exceptions import ApiError
from alerta.models.user import User
from alerta.utils.api import absolute_url
from . import auth


@auth.route('/auth/signup', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def signup():
    try:
        user = User.parse(request.json)
    except Exception as e:
        raise ApiError(str(e), 400)

    if User.get_by_email(email=user.email):
        raise ApiError("username already exists", 409)

    try:
        user = user.create()
    except Exception as e:
        ApiError(str(e), 500)

    # if email verification is enforced, deny login and send email
    if current_app.config['EMAIL_VERIFICATION'] and not user.email_verified:
        hash = str(uuid4())
        send_confirmation(user, hash)
        user.set_email_hash(hash)
        raise ApiError('email not verified', 401)

    # check user is active
    if user.status != 'active':
        raise ApiError('user not active', 403)

    # check allowed domain
    if is_authorized('ALLOWED_EMAIL_DOMAINS', groups=[user.domain]):
        raise ApiError("unauthorized domain", 403)

    # assign customer & update last login time
    customer = get_customer(user.email, groups=[user.domain])
    user.update_last_login()

    # generate token
    token = create_token(user.id, user.name, user.email, provider='basic', customer=customer,
                         roles=user.roles, email=user.email, email_verified=user.email_verified)
    return jsonify(token=token.tokenize)


@auth.route('/auth/login', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def login():
    # lookup user from username/email
    try:
        username = request.json.get('username', None) or request.json['email']
        password = request.json['password']
    except KeyError:
        raise ApiError("must supply 'username' and 'password'", 401)

    user = User.get_by_email(email=username)
    if not user:
        raise ApiError("invalid username or password", 401)

    if not user.verify_password(password):
        raise ApiError("invalid username or password", 401)

    # if email verification is enforced, deny login and send email
    if current_app.config['EMAIL_VERIFICATION'] and not user.email_verified:
        hash = str(uuid4())
        send_confirmation(user, hash)
        user.set_email_hash(hash)
        raise ApiError('email not verified', 401)

    # check user is active
    if user.status != 'active':
        raise ApiError('user not active', 403)

    # check allowed domain
    if is_authorized('ALLOWED_EMAIL_DOMAINS', groups=[user.domain]):
        raise ApiError("unauthorized domain", 403)

    # assign customer & update last login time
    customer = get_customer(user.email, groups=[user.domain])
    user.update_last_login()

    # generate token
    token = create_token(user.id, user.name, user.email, provider='basic', customer=customer,
                         roles=user.roles, email=user.email, email_verified=user.email_verified)
    return jsonify(token=token.tokenize)


@auth.route('/auth/confirm/<hash>', methods=['GET'])
def verify_email(hash):

    user = User.verify_hash(hash)
    if user and not user.email_verified:
        user.set_email_verified()
        return render_template('auth/verify_success.html', email=user.email)
    else:
        return render_template('auth/verify_failed.html')


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
