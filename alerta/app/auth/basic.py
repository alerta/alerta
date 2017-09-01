
import logging
from uuid import uuid4

from flask import current_app, request, jsonify, render_template
from flask_cors import cross_origin

from alerta.app.utils.api import absolute_url
from alerta.app.exceptions import ApiError, NoCustomerMatch
from alerta.app.models.user import User
from alerta.app.models.customer import Customer

from alerta.app.auth.utils import is_authorized, create_token

from . import auth


@auth.route('/auth/signup', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def signup():
    try:
        user = User.parse(request.json)
    except Exception as e:
        raise ApiError(str(e), 400)

    if User.get_by_email(user.email):
        raise ApiError("user already exists", 409)

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

    # check allowed domain
    if is_authorized('ALLOWED_EMAIL_DOMAINS', groups=[user.domain]):
        raise ApiError("unauthorized domain", 403)

    # assign customer
    if current_app.config['CUSTOMER_VIEWS']:
        try:
            customer = Customer.lookup(user.email, groups=[user.domain])
        except NoCustomerMatch as e:
            raise ApiError(str(e), 403)
    else:
        customer = None

    user.update_last_login()

    # generate token
    token = create_token(user.id, user.name, user.email, provider='basic', customer=customer,
                         roles=[user.role], email=user.email, email_verified=user.email_verified)
    return jsonify(token=token.tokenize)


@auth.route('/auth/login', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def login():
    # lookup user from login/email
    try:
        email = request.json['email']
        password = request.json['password']
    except KeyError:
        raise ApiError("must supply 'email' and 'password'", 401)

    user = User.get_by_email(email)
    if not user:
        raise ApiError("invalid user", 401)

    if not user.verify_password(password):
        raise ApiError("invalid password", 401)

    if current_app.config['EMAIL_VERIFICATION'] and not user.email_verified:
        hash = str(uuid4())
        send_confirmation(user, hash)
        user.set_email_hash(hash)
        raise ApiError('email not verified', 401)

    if is_authorized('ALLOWED_EMAIL_DOMAINS', groups=[user.domain]):
        raise ApiError("unauthorized domain", 403)

    # assign customer
    if current_app.config['CUSTOMER_VIEWS']:
        try:
            customer = Customer.lookup(user.email, groups=[user.domain])
        except NoCustomerMatch as e:
            raise ApiError(str(e), 403)
    else:
        customer = None

    user.update_last_login()

    # generate token
    token = create_token(user.id, user.name, user.email, provider='basic', customer=customer,
                         roles=[user.role], email=user.email, email_verified=user.email_verified)
    return jsonify(token=token.tokenize)


@auth.route('/auth/confirm/<hash>', methods=['GET'])
def verify_email(hash):

    user = User.verify_hash(hash)
    if not user.email_verified:
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

    msg = MIMEMultipart('related')
    msg['Subject'] = "[Alerta] Please verify your email '%s'" % user.email
    msg['From'] = current_app.config['MAIL_FROM']
    msg['To'] = user.email
    msg.preamble = "[Alerta] Please verify your email '%s'" % user.email

    text = 'Hello {name}!\n\n' \
           'Please verify your email address is {email} by clicking on the link below:\n\n' \
           '{url}\n\n' \
           'You\'re receiving this email because you recently created a new Alerta account.' \
           ' If this wasn\'t you, please ignore this email.'.format(
               name=user.name, email=user.email, url=absolute_url('/auth/confirm/' + hash))

    msg_text = MIMEText(text, 'plain', 'utf-8')
    msg.attach(msg_text)

    try:
        mx = smtplib.SMTP(current_app.config['SMTP_HOST'], current_app.config['SMTP_PORT'])
        if current_app.config['DEBUG']:
            mx.set_debuglevel(True)
        mx.ehlo()
        mx.starttls()
        mx.login(current_app.config['MAIL_FROM'], current_app.config['SMTP_PASSWORD'])
        mx.sendmail(current_app.config['MAIL_FROM'], [user.email], msg.as_string())
        mx.close()
    except smtplib.SMTPException as e:
        logging.error('Failed to send email : %s', str(e))
    except (socket.error, socket.herror, socket.gaierror) as e:
        logging.error('Mail server connection error: %s', str(e))
        return
    except Exception as e:
        logging.error('Unhandled exception: %s', str(e))
