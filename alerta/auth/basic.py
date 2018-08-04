
from uuid import uuid4

from flask import current_app, request, jsonify, render_template
from flask_cors import cross_origin

from alerta.auth.utils import not_authorized, create_token, get_customers, send_confirmation
from alerta.exceptions import ApiError
from alerta.models.user import User
from . import auth


@auth.route('/auth/signup', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def signup():
    try:
        user = User.parse(request.json)
    except Exception as e:
        raise ApiError(str(e), 400)

    # set sign-up defaults
    user.roles = ['user']
    user.email_verified = False

    # check allowed domain
    if not_authorized('ALLOWED_EMAIL_DOMAINS', groups=[user.domain]):
        raise ApiError("unauthorized domain", 403)

    if User.find_by_email(email=user.email):
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
        raise ApiError("Invalid username or password", 401)

    # if email verification is enforced, deny login and send email
    if current_app.config['EMAIL_VERIFICATION'] and not user.email_verified:
        hash = str(uuid4())
        send_confirmation(user, hash)
        user.set_email_hash(hash)
        raise ApiError('email not verified', 401)

    # check allowed domain
    if not_authorized('ALLOWED_EMAIL_DOMAINS', groups=[user.domain]):
        raise ApiError("unauthorized domain", 403)

    # assign customers
    customers = get_customers(user.email, groups=[user.domain])

    # generate token
    token = create_token(user.id, user.name, user.email, provider='basic', customers=customers,
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
