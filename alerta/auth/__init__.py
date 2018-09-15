from flask import Blueprint, request

from alerta.exceptions import ApiError

auth = Blueprint('auth', __name__)


try:
    import ldap  # noqa
    from . import basic_ldap  # noqa
except ImportError:
    from . import basic  # noqa

from . import github, gitlab, google, keycloak, pingfederate, saml2, userinfo  # noqa


@auth.before_request
def only_json():
    # SAML2 Assertion Consumer Service expects POST request with 'Content-Type': 'application/x-www-form-urlencoded' from IdP
    if request.method == 'POST' and request.path == '/auth/saml' and request.headers['Content-Type'] == 'application/x-www-form-urlencoded':
        return
    if request.method in ['POST', 'PUT'] and not request.is_json:
        raise ApiError("POST and PUT requests must set 'Content-Type' to 'application/json'", 415)
