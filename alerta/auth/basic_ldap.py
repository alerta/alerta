import sys

import ldap  # pylint: disable=import-error
from flask import current_app, jsonify, request

from alerta.auth.utils import create_token, get_customers
from alerta.exceptions import ApiError
from alerta.models.permission import Permission
from alerta.models.user import User
from alerta.utils.audit import auth_audit_trail


def login():

    # Allow LDAP server to use a self signed certificate
    if current_app.config['LDAP_ALLOW_SELF_SIGNED_CERT']:
        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_ALLOW)

    # Retrieve required fields from client request
    try:
        login = request.json.get('username', None) or request.json['email']
        password = request.json['password']
    except KeyError:
        raise ApiError("must supply 'username' and 'password'", 401)

    try:
        if '\\' in login:
            domain, username = login.split('\\')
            email = ''
            email_verified = False
        else:
            username, domain = login.split('@')
            email = login
            email_verified = True
    except ValueError:
        raise ApiError('expected username with domain', 401)

    # Validate LDAP domain
    if domain not in current_app.config['LDAP_DOMAINS'] and \
       domain not in current_app.config['LDAP_DOMAINS_SEARCH_QUERY']:
        raise ApiError('unauthorized domain', 403)

    # Initialise ldap connection
    try:
        trace_level = 2 if current_app.debug else 0
        ldap_connection = ldap.initialize(current_app.config['LDAP_URL'], trace_level=trace_level)
    except Exception as e:
        raise ApiError(str(e), 500)

    # If user search filter exist
    #   Search the user using the provided User Search filter for the current domain
    #   If one user is found
    #       Set the DN as the one found
    #       Set email retreived from AD
    #   If more than one user is found
    #       Except: Search query is bad defined
    # Else
    #   Set the DN as the one found in LDAP_DOMAINS variable
    domain_search_query = current_app.config.get('LDAP_DOMAINS_SEARCH_QUERY', {})
    base_dns = current_app.config.get('LDAP_DOMAINS_BASEDN', {})
    user_base_dn = current_app.config.get('LDAP_DOMAINS_USER_BASEDN', {})
    if domain in domain_search_query:
        ldap_bind_username = current_app.config.get('LDAP_BIND_USERNAME', '')
        ldap_bind_password = current_app.config.get('LDAP_BIND_PASSWORD', '')

        try:
            ldap_connection.simple_bind_s(ldap_bind_username, ldap_bind_password)
        except ldap.INVALID_CREDENTIALS:
            raise ApiError('invalid ldap bind username or password', 401)

        ldap_users = [(_dn, user) for _dn, user in ldap_connection.search_s(
            base_dns[domain] if user_base_dn.get(domain) is None else user_base_dn[domain],
            ldap.SCOPE_SUBTREE,
            domain_search_query[domain].format(username=username, email=email),
            ['mail']
        ) if _dn is not None]

        if len(ldap_users) > 1:
            raise ApiError('invalid search query for domain "{}"'.format(domain), 500)
        elif len(ldap_users) == 0:
            raise ApiError('invalid username or password', 401)

        for _dn, _email in ldap_users:
            userdn = _dn
            email_attr = _email.get('mail')
            if email_attr is not None:
                email = email_attr[0].decode(sys.stdout.encoding)
                email_verified = True
    else:
        userdn = current_app.config['LDAP_DOMAINS'][domain] % username

    # Attempt LDAP AUTH
    try:
        ldap_connection.simple_bind_s(userdn, password)
    except ldap.INVALID_CREDENTIALS:
        raise ApiError('invalid username or password', 401)
    except Exception as e:
        raise ApiError(str(e), 500)

    # Get email address from LDAP
    if not email_verified:
        try:
            ldap_result = ldap_connection.search_s(userdn, ldap.SCOPE_SUBTREE, '(objectClass=*)', ['mail'])
            email = ldap_result[0][1]['mail'][0].decode(sys.stdout.encoding)
            email_verified = True
        except Exception:
            email = '{}@{}'.format(username, domain)

    # Create user if not yet there
    user = User.find_by_username(username=login)
    if not user:
        user = User(name=username, login=login, password='', email=email,
                    roles=[], text='LDAP user', email_verified=email_verified)
        try:
            user = user.create()
        except Exception as e:
            ApiError(str(e), 500)

    # Assign customers & update last login time
    groups = list()
    try:
        groups_filters = current_app.config.get('LDAP_DOMAINS_GROUP', {})
        groups_base_dn = current_app.config.get('LDAP_DOMAINS_GROUP_BASEDN', {})
        if domain in groups_filters and (domain in base_dns or domain in groups_base_dn):
            resultID = ldap_connection.search(
                base_dns[domain] if groups_base_dn.get(domain) is None else groups_base_dn[domain],
                ldap.SCOPE_SUBTREE,
                groups_filters[domain].format(username=username, email=email, userdn=userdn),
                ['cn']
            )
            resultTypes, results = ldap_connection.result(resultID)
            for _dn, attributes in results:
                if _dn is not None:
                    groups.append(attributes['cn'][0].decode('utf-8'))
    except ldap.LDAPError as e:
        raise ApiError(str(e), 500)

    # Check user is active
    if user.status != 'active':
        raise ApiError('User {} not active'.format(login), 403)
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
