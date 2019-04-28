
import ldap
from flask import current_app, jsonify, request
from flask_cors import cross_origin

from alerta.auth.utils import create_token, get_customers
from alerta.exceptions import ApiError
from alerta.models.permission import Permission
from alerta.models.user import User
from alerta.utils.audit import auth_audit_trail

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

    username, domain = email.split('@')

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
    user = User.find_by_username(username=email)
    if not user:
        user = User(name=username, login=email, password='', email=email,
                    roles=[], text='LDAP user', email_verified=True)
        try:
            user = user.create()
        except Exception as e:
            ApiError(str(e), 500)

    # Assign customers & update last login time
    groups = list()
    try:
        groups_filters = current_app.config.get('LDAP_DOMAINS_GROUP', {})
        base_dns = current_app.config.get('LDAP_DOMAINS_BASEDN', {})
        if domain in groups_filters and domain in base_dns:
            resultID = ldap_connection.search(
                base_dns[domain],
                ldap.SCOPE_SUBTREE,
                groups_filters[domain].format(username=username, email=email, userdn=userdn),
                ['cn']
            )
            resultTypes, results = ldap_connection.result(resultID)
            for _dn, attributes in results:
                groups.append(attributes['cn'][0].decode('utf-8'))
    except ldap.LDAPError as e:
        raise ApiError(str(e), 500)

    # Check user is active
    if user.status != 'active':
        raise ApiError('User {} not active'.format(email), 403)
    user.update_last_login()

    scopes = Permission.lookup(login=user.email, roles=user.roles)
    customers = get_customers(login=user.email, groups=[user.domain] + groups)

    auth_audit_trail.send(current_app._get_current_object(), event='basic-ldap-login', message='user login via LDAP',
                          user=user.email, customers=customers, scopes=scopes, resource_id=user.id, type='user',
                          request=request)

    # Generate token
    token = create_token(user_id=user.id, name=user.name, login=user.email, provider='ldap', customers=customers,
                         scopes=scopes, roles=user.roles, email=user.email, email_verified=user.email_verified)
    return jsonify(token=token.tokenize)
