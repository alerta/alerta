
import ldap
from flask import current_app, jsonify, request
from flask_cors import cross_origin

from alerta.auth.utils import create_token, get_customers
from alerta.exceptions import ApiError
from alerta.models.user import User

from . import auth


@auth.route('/auth/login', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def login():
    # Retrieve required fields from client request
    try:
        email = request.json.get('username', None) or request.json['email']
        password = request.json['password']
    except KeyError:
        raise ApiError("must supply 'username' and 'password'", 401)

    username = email.split('@')[0]
    domain = email.split('@')[1]

    # Validate LDAP domain
    if domain not in current_app.config['LDAP_DOMAINS']:
        raise ApiError('unauthorized domain', 403)

    userdn = current_app.config['LDAP_DOMAINS'][domain] % username

    # Attempt LDAP AUTH
    try:
        trace_level = 2 if current_app.debug else 0
        ldap_connection = ldap.initialize(current_app.config['LDAP_URL'], trace_level=trace_level)
        ldap_connection.simple_bind_s(userdn, password)
    except ldap.INVALID_CREDENTIALS:
        raise ApiError('invalid username or password', 401)
    except Exception as e:
        raise ApiError(str(e), 500)

    # Create user if not yet there
    user = User.find_by_email(email=email)
    if not user:
        user = User(username, email, '', ['user'], 'LDAP user', email_verified=True)
        user.create()

    # Check user is active
    if user.status != 'active':
        raise ApiError('user not active', 403)

    # Assign customers & update last login time
    customers = get_customers(user.email, groups=[user.domain])
    user.update_last_login()

    # Generate token
    token = create_token(user.id, user.name, user.email, provider='basic_ldap', customers=customers,
                         roles=user.roles, email=user.email, email_verified=user.email_verified)
    return jsonify(token=token.tokenize)
