from flask import Blueprint, request

from alerta.exceptions import ApiError


class AuthBlueprint(Blueprint):

    def register(self, app, options, first_registration=False):
        if app.config['AUTH_PROVIDER'] in ['openid', 'azure', 'cognito', 'gitlab', 'keycloak']:
            oidc_config, _ = oidc.get_oidc_configuration(app)
            app.config['OIDC_AUTH_URL'] = oidc_config['authorization_endpoint']
        super().register(app, options, first_registration)


auth = AuthBlueprint('auth', __name__)


def init_auth(app):
    if app.config['AUTH_PROVIDER'] == 'ldap':
        try:
            import ldap  # noqa
            from . import basic_ldap  # noqa
        except ImportError:
            raise RuntimeError('Must install python-ldap to use LDAP authentication module')
    else:
        from . import basic  # noqa

    if app.config['AUTH_PROVIDER'] == 'saml2':
        try:
            import saml2  # noqa
            from . import saml  # noqa
        except ImportError:
            raise RuntimeError('Must install pysaml2 to use SAML2 authentication module')


from . import github, oidc, userinfo  # noqa


@auth.before_request
def only_json():
    # SAML2 Assertion Consumer Service expects POST request with 'Content-Type': 'application/x-www-form-urlencoded' from IdP
    if request.method == 'POST' and request.path == '/auth/saml' and request.headers['Content-Type'] == 'application/x-www-form-urlencoded':
        return
    if request.method in ['POST', 'PUT'] and not request.is_json:
        raise ApiError("POST and PUT requests must set 'Content-Type' to 'application/json'", 415)
