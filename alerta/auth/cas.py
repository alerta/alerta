import json
import logging

import defusedxml.ElementTree as ET
import requests
from flask import current_app, jsonify, request
from flask_cors import cross_origin

from alerta.auth.utils import create_token, get_customers, not_authorized
from alerta.exceptions import ApiError
from alerta.models.permission import Permission
from alerta.models.user import User
from alerta.utils.audit import auth_audit_trail

from . import auth

LOG = logging.getLogger('alerta.auth.cas')


def flatten_attrs(raw_attrs: dict) -> dict:
    """
    Convert { key: [v] } into { key: v } when the list has a single element.
    Leaves lists intact if they have multiple values.
    """
    return {
        key: vals[0] if isinstance(vals, (list, tuple)) and len(vals) == 1 else vals
        for key, vals in raw_attrs.items()
    }


def validate_cas(ticket, service, cas_server, validate_route='/serviceValidate'):
    """
    Validate a CAS ticket, with configurable response format.
    Reads current_app.config["CAS_RESPONSE_TYPE"] (AUTO, JSON or XML).

    Returns:
      (True,  username, attributes_dict, raw_response)
    or (False, None,    {},                raw_response)
    """
    # Determine desired format
    fmt = current_app.config.get('CAS_RESPONSE_TYPE', 'AUTO').upper()
    if fmt not in ('AUTO', 'JSON', 'XML'):
        fmt = 'AUTO'

    # Build request parameters
    url = f"{cas_server.rstrip('/')}{validate_route}"
    params = {'ticket': ticket, 'service': service}

    # Only add format=JSON when explicit or in AUTO mode
    want_json = fmt in ('AUTO', 'JSON')
    if want_json:
        params['format'] = 'JSON'

    try:
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
    except requests.RequestException as e:
        LOG.exception('Failed to contact CAS server')
        raise ApiError(f'Unable to contact CAS server: {e}', 503)

    ct = resp.headers.get('Content-Type', '')

    # --- JSON PATH ---
    if want_json and 'application/json' in ct:
        try:
            data = resp.json()
        except ValueError as e:
            LOG.exception('Failed to parse CAS JSON response')
            # If we're in AUTO, fall back to XML parsing
            if fmt == 'AUTO':
                LOG.debug('Falling back to XML parsing due to JSON parse error')
            else:
                raise ApiError(f'Malformed CAS JSON response: {e}', 502)
        else:
            svc = data.get('serviceResponse', {})
            success = svc.get('authenticationSuccess')
            if success:
                username = success.get('user')
                raw_attrs = success.get('attributes', {}) or {}
                attrs = flatten_attrs(raw_attrs)
                LOG.info('CAS authentication succeeded for user %s', username)
                return True, username, attrs, data
            # JSON auth failure
            failure = svc.get('authenticationFailure', {})
            code, desc = failure.get('code'), failure.get('description')
            LOG.warning('CAS authentication failed [%s]: %s', code, desc)
            return False, None, {}, data

    # If we get here, either:
    #  - JSON was not requested/supported, or
    #  - JSON branch fell through in AUTO mode
    # --- XML PATH ---
    try:
        root = ET.fromstring(resp.text)
        ns = {'cas': 'http://www.yale.edu/tp/cas'}

        # authenticationFailure?
        failure = root.find('cas:authenticationFailure', ns)
        if failure is not None:
            code = failure.get('code')
            msg = (failure.text or '').strip()
            LOG.warning('CAS XML authenticationFailure [%s]: %s', code, msg)
            return False, None, {}, resp.text

        # authenticationSuccess?
        success = root.find('cas:authenticationSuccess', ns)
        if success is None:
            LOG.error('No <cas:authenticationSuccess> in XML response')
            return False, None, {}, resp.text

        username = success.findtext('cas:user', None, ns)

        # collect attributes
        raw_attrs = {}
        attr_block = success.find('cas:attributes', ns)
        if attr_block is not None:
            for child in attr_block:
                key = child.tag.split('}', 1)[-1]
                raw_attrs[key] = child.text

        attrs = flatten_attrs(raw_attrs)
        return True, username, attrs, resp.text

    except ET.ParseError as e:
        LOG.exception('Failed to parse CAS XML response')
        raise ApiError(f'Malformed CAS XML response: {e}', 502)


@auth.route('/auth/cas', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def cas_login():
    if request.method == 'OPTIONS':
        return '', 204

    ticket = request.json.get('ticket')
    service = request.json.get('service')
    if not ticket or not service:
        raise ApiError("Fields 'ticket' and 'service' are required", 400)

    cas_server = current_app.config['CAS_SERVER']
    if not cas_server:
        raise ApiError('Missing CAS_SERVER configuration', 500)

    success, cas_username, attrs, raw = validate_cas(ticket, service, cas_server)

    LOG.debug('Full CAS response:\n%s', json.dumps(raw, indent=2) if isinstance(raw, dict) else raw)

    if not success:
        raise ApiError('Invalid CAS ticket', 401)

    # Map CAS attributes to Alerta User model
    login = cas_username
    email = attrs.get('mail') or attrs.get('email')
    role_claim = current_app.config.get('CAS_ROLE_CLAIM', 'roles')
    group_claim = current_app.config.get('CAS_GROUP_CLAIM', 'groups')

    # Ensure lists
    raw_roles = attrs.get(role_claim, [])
    raw_groups = attrs.get(group_claim, [])
    if isinstance(raw_roles, str):
        raw_roles = [raw_roles]
    if isinstance(raw_groups, str):
        raw_groups = [raw_groups]

    user = User.find_by_id(id=login)
    if not user:
        user = User(
            id=login,
            name=attrs.get('displayName', login),
            login=login,
            password='',
            email=email,
            roles=current_app.config['USER_ROLES'],
            text='',
            email_verified=True,
        )
        user.create()
    else:
        user.update(login=login, email=email)

    # Merge roles and groups
    roles = list(set(raw_roles + user.roles))
    groups = raw_groups
    subject = login

    if user.status != 'active':
        raise ApiError(f'User {login} is not active', 403)
    if not_authorized('ALLOWED_EMAIL_DOMAINS', groups=[user.domain]):
        raise ApiError(f'User {login} is not authorized', 403)

    user.update_last_login()

    scopes = Permission.lookup(login, roles=roles)
    customers = get_customers(login, groups=groups + ([user.domain] if user.domain else []))

    auth_audit_trail.send(
        current_app._get_current_object(),
        event='cas-login',
        message='User login via CAS',
        user=login,
        customers=customers,
        scopes=scopes,
        roles=roles,
        groups=groups,
        resource_id=subject,
        type='user',
        request=request,
    )

    token = create_token(
        user_id=subject,
        name=user.name,
        login=login,
        provider='cas',
        customers=customers,
        scopes=scopes,
        roles=roles,
        groups=groups,
        email=email,
        email_verified=True,
        picture=None,
    )

    return jsonify(token=token.tokenize())
