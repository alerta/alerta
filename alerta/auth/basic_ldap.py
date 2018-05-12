
import logging
from uuid import uuid4

from flask import current_app, request, jsonify, render_template
from flask_cors import cross_origin

from alerta.auth.utils import is_authorized, create_token, get_customers
from alerta.exceptions import ApiError
from alerta.models.user import User
from alerta.utils.api import absolute_url
from . import auth

import ldap

@auth.route('/auth/signup', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def signup():
    raise NotImplementedError

@auth.route('/auth/login', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def login():
    # Retrieve required fields from client request
    try:
        email = request.json.get('username', None) or request.json['email']
        password = request.json['password']
    except KeyError:
        raise ApiError("must supply 'username' and 'password'", 401)

    username = email.split("@")[0]
    domain = email.split("@")[1]

    # Validate LDAP domain
    if not 'LDAP_DOMAINS' in current_app.config:
        raise ApiError("LDAP_DOMAINS not configured", 500)

    if domain not in current_app.config["LDAP_DOMAINS"]:
        raise ApiError("unauthorized domain", 403)

    userdn = current_app.config["LDAP_DOMAINS"][domain] % username

    # Attempt LDAP AUTH
    try:
        ldap_connection = ldap.initialize(current_app.config['LDAP_SERVER'])
        ldap_connection.simple_bind_s(userdn, password)

    except ldap.INVALID_CREDENTIALS:
        raise ApiError("invalid username or password", 401)

    except:
        raise ApiError("logon failed", 500)

    # Create user if not yet there
    user = User.find_by_email(email=email)
    if not user:
        user = User(username, email, "", ["user"], "LDAP user")
        user.create()
        user.set_email_verified()

    # Check user is active
    if user.status != 'active':
        raise ApiError('user not active', 403)

    # Assign customers & update last login time
    customers = get_customers(user.email, groups=[user.domain])
    user.update_last_login()

    # Generate token
    token = create_token(user.id, user.name, user.email, provider='basic', customers=customers,
                         roles=user.roles, email=user.email, email_verified=user.email_verified)
    return jsonify(token=token.tokenize)
