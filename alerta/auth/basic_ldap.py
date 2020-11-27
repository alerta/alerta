import ldap  # pylint: disable=import-error
from flask import current_app, jsonify, request

from alerta.auth.utils import create_token, get_customers, not_authorized
from alerta.exceptions import ApiError
from alerta.models.permission import Permission
from alerta.models.user import User
from alerta.utils.audit import auth_audit_trail


def login():

    try:
        login = request.json.get('username') or request.json['email']
        password = request.json['password']
    except KeyError:
        raise ApiError("must supply 'username' and 'password'", 401)

    if not password:
        raise ApiError('password not allowed to be empty', 401)

    try:
        if '\\' in login:
            domain, username = login.split('\\')
        else:
            username, domain = login.split('@')
    except ValueError:
        if current_app.config['LDAP_DEFAULT_DOMAIN']:
            username = login
            domain = current_app.config['LDAP_DEFAULT_DOMAIN']
        else:
            raise ApiError('expected username with domain', 401)

    # Validate LDAP domain
    if (domain not in current_app.config['ALLOWED_EMAIL_DOMAINS']
            and domain not in current_app.config['LDAP_DOMAINS']):
        raise ApiError('unauthorized domain', 403)

    # LDAP certificate settings
    if current_app.config['LDAP_CACERT']:
        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_HARD)
        ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, current_app.config['LDAP_CACERT'])

    # Allow LDAP server to use a self-signed certificate
    if current_app.config['LDAP_ALLOW_SELF_SIGNED_CERT']:
        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_ALLOW)

    # Set LDAP Timeout
    if current_app.config['LDAP_TIMEOUT']:
        ldap.set_option(ldap.OPT_NETWORK_TIMEOUT, current_app.config['LDAP_TIMEOUT'])

    # Set custom config options
    for k, v in current_app.config['LDAP_CONFIG'].items():
        ldap.set_option(getattr(ldap, k), v)

    # Initialise ldap connection
    try:
        trace_level = 2 if current_app.debug else 0  # XXX - do not set in production environments
        ldap_connection = ldap.initialize(current_app.config['LDAP_URL'], trace_level=trace_level)
    except Exception as e:
        raise ApiError(str(e), 500)

    # bind user credentials
    ldap_bind_username = current_app.config['LDAP_BIND_USERNAME']
    ldap_bind_password = current_app.config['LDAP_BIND_PASSWORD']
    if ldap_bind_username:
        try:
            ldap_connection.simple_bind_s(ldap_bind_username, ldap_bind_password)
        except ldap.INVALID_CREDENTIALS:
            raise ApiError('invalid ldap bind credentials', 500)

    # Set default base DN for user and group search
    base_dn = current_app.config['LDAP_BASEDN']

    # If user search filter exist
    #   Search the user using the provided User Search filter for the current domain
    #   If one user is found
    #       Set the DN as the one found
    #       Set email retreived from AD
    #   If more than one user is found
    #       Except: Search query is bad defined
    # Else
    #   Set the DN as the one found in LDAP_DOMAINS variable
    user_filter = current_app.config['LDAP_USER_FILTER']
    user_base_dn = current_app.config['LDAP_USER_BASEDN']
    user_attrs = [
        current_app.config['LDAP_USER_NAME_ATTR'],
        current_app.config['LDAP_USER_EMAIL_ATTR']
    ]
    if user_filter:
        result = [r for r in ldap_connection.search_s(
            base=user_base_dn or base_dn,
            scope=ldap.SCOPE_SUBTREE,
            filterstr=user_filter.format(username=username),
            attrlist=user_attrs
        ) if None not in r]

        if len(result) > 1:
            raise ApiError('invalid search query for domain "{}"'.format(domain), 500)
        elif len(result) == 0:
            raise ApiError('invalid username or password', 401)
        user_dn = result[0][0]
        name = result[0][1][current_app.config['LDAP_USER_NAME_ATTR']][0].decode('utf-8', 'ignore')
        email = result[0][1][current_app.config['LDAP_USER_EMAIL_ATTR']][0].decode('utf-8', 'ignore')
        email_verified = bool(email)
    else:
        if '%' in current_app.config['LDAP_DOMAINS'][domain]:
            user_dn = current_app.config['LDAP_DOMAINS'][domain] % username
        else:
            user_dn = current_app.config['LDAP_DOMAINS'][domain].format(username)
        name = username
        email = '{}@{}'.format(username, domain)
        email_verified = False

    # Authenticate user logging in
    try:
        ldap_connection.simple_bind_s(user_dn, password)
    except ldap.INVALID_CREDENTIALS:
        raise ApiError('invalid username or password', 401)

    login = email or username
    user = User.find_by_username(username=login)
    if not user:
        user = User(name=name, login=login, password='', email=email,
                    roles=current_app.config['USER_ROLES'], text='LDAP user', email_verified=email_verified)
        user = user.create()
    else:
        user.update(login=login, email=email, email_verified=email_verified)

    if ldap_bind_username:
        try:
            ldap_connection.simple_bind_s(ldap_bind_username, ldap_bind_password)
        except ldap.INVALID_CREDENTIALS:
            raise ApiError('invalid ldap bind credentials', 500)

    # Assign customers & update last login time
    group_filter = current_app.config['LDAP_GROUP_FILTER']
    group_base_dn = current_app.config['LDAP_GROUP_BASEDN']
    groups = list()
    if group_filter:
        result = ldap_connection.search_s(
            base=group_base_dn or base_dn,
            scope=ldap.SCOPE_SUBTREE,
            filterstr=group_filter.format(username=username, email=email, userdn=user_dn),
            attrlist=[current_app.config['LDAP_GROUP_NAME_ATTR']]
        )
        for group_dn, group_attrs in result:
            if current_app.config['LDAP_GROUP_NAME_ATTR'] in group_attrs.keys():
                groups.extend([g.decode('utf-8', 'ignore') for g in group_attrs[current_app.config['LDAP_GROUP_NAME_ATTR']]])
            else:
                groups.append(group_dn)

    # Check user is active
    if user.status != 'active':
        raise ApiError('User {} not active'.format(login), 403)
    if not_authorized('ALLOWED_LDAP_GROUPS', groups):
        raise ApiError('User {} is not authorized'.format(login), 403)
    user.update_last_login()

    scopes = Permission.lookup(login=login, roles=user.roles + groups)
    customers = get_customers(login=login, groups=[user.domain] + groups)

    auth_audit_trail.send(current_app._get_current_object(), event='basic-ldap-login', message='user login via LDAP',
                          user=login, customers=customers, scopes=scopes, roles=user.roles, groups=groups,
                          resource_id=user.id, type='user', request=request)

    # Generate token
    token = create_token(user_id=user.id, name=user.name, login=user.email, provider='ldap',
                         customers=customers, scopes=scopes, roles=user.roles, groups=groups,
                         email=user.email, email_verified=user.email_verified)
    return jsonify(token=token.tokenize)
