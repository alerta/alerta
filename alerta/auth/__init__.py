from flask import Blueprint, request

from alerta.exceptions import ApiError

auth = Blueprint('auth', __name__) 

def init_app(app):
    from . import github, gitlab, google, keycloak, pingfederate, saml2, userinfo
    
    # If LDAP_SERVER is defined in config then use basic_ldap instead of basic to provide LDAP authentication
    if "LDAP_SERVER" in app.config:
        from . import basic_ldap
    else:
        from . import basic

@auth.before_request
def only_json():
    if request.method in ['POST', 'PUT'] and not request.is_json:
        raise ApiError("POST and PUT requests must set 'Content-type' to 'application/json'", 415)