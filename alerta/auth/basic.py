from flask import current_app, jsonify, request
from flask_cors import cross_origin

from alerta.auth.utils import create_token, get_customers, not_authorized
from alerta.exceptions import ApiError
from alerta.models.user import User

from . import auth


@auth.route('/auth/signup', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def signup():

    if not current_app.config['SIGNUP_ENABLED']:
        raise ApiError('user signup is disabled', 401)

    try:
        user = User.parse(request.json)
    except Exception as e:
        raise ApiError(str(e), 400)

    # set sign-up defaults
    user.roles = ['user']
    user.email_verified = False

    # check allowed domain
    if not_authorized('ALLOWED_EMAIL_DOMAINS', groups=[user.domain]):
        raise ApiError('unauthorized domain', 403)

    if User.find_by_email(email=user.email):
        raise ApiError('username already exists', 409)

    try:
        user = user.create()
    except Exception as e:
        ApiError(str(e), 500)

    # if email verification is enforced, deny login and send email
    if current_app.config['EMAIL_VERIFICATION'] and not user.email_verified:
        user.send_confirmation()
        raise ApiError('email not verified', 401)

    # check user is active & update last login
    if user.status != 'active':
        raise ApiError('user not active', 403)
    user.update_last_login()

    # assign customers
    customers = get_customers(user.email, groups=[user.domain])

    # generate token
    token = create_token(user.id, user.name, user.email, provider='basic', customers=customers,
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

    user = User.check_credentials(username, password)
    if not user:
        raise ApiError('Invalid username or password', 401)

    # if email verification is enforced, deny login and send email
    if current_app.config['EMAIL_VERIFICATION'] and not user.email_verified:
        user.send_confirmation()
        raise ApiError('email not verified', 401)

    # check allowed domain
    if not_authorized('ALLOWED_EMAIL_DOMAINS', groups=[user.domain]):
        raise ApiError('unauthorized domain', 403)

    # assign customers
    customers = get_customers(user.email, groups=[user.domain])

    # generate token
    token = create_token(user.id, user.name, user.email, provider='basic', customers=customers,
                         roles=user.roles, email=user.email, email_verified=user.email_verified)
    return jsonify(token=token.tokenize)


@auth.route('/auth/confirm/<hash>', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def verify_email(hash):

    user = User.verify_hash(hash, salt='confirm')
    if user:
        if user.email_verified:
            raise ApiError('email already verified', 400)
        user.set_email_verified()
        return jsonify(status='ok', message='email address {} confirmed'.format(user.email))
    else:
        raise ApiError('invalid confirmation hash', 400)


@auth.route('/auth/forgot', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def forgot():
    try:
        email = request.json['email']
    except KeyError:
        raise ApiError("must supply 'email'", 400)

    user = User.find_by_email(email)
    if user:
        if not user.is_active:
            raise ApiError('user not active', 403)
        user.send_password_reset()

        return jsonify(status='ok', message='password reset sent')
    else:
        raise ApiError('invalid email address', 400)


@auth.route('/auth/reset/<hash>', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def reset(hash):
    try:
        password = request.json['password']
    except KeyError:
        raise ApiError("must supply 'password'", 400)

    user = User.verify_hash(hash, salt='reset')
    if user:
        if not user.is_active:
            raise ApiError('user not active', 403)
        user.reset_password(password)

        return jsonify(status='ok', message='password reset successful')
    else:
        raise ApiError('invalid password reset hash', 400)
