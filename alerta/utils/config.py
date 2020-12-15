import os

from flask import Flask


class Config:

    def __init__(self, app: Flask = None) -> None:
        self.app = None
        if app:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        config = self.get_user_config()
        app.config.update(config)

    @staticmethod
    def get_user_config():
        from flask import Config
        config = Config('/')

        config.from_object('alerta.settings')
        config.from_pyfile('/etc/alertad.conf', silent=True)
        config.from_envvar('ALERTA_SVR_CONF_FILE', silent=True)

        config['DEBUG'] = get_config('DEBUG', default=True, type=bool, config=config)
        config['BASE_URL'] = get_config('BASE_URL', default='', type=str, config=config)
        config['USE_PROXYFIX'] = get_config('USE_PROXYFIX', default=False, type=bool, config=config)
        config['SECRET_KEY'] = get_config('SECRET_KEY', default='', type=str, config=config)

        database_url = (
            # The following database settings are deprecated.
            os.environ.get('MONGO_URI', None)
            or os.environ.get('MONGODB_URI', None)
            or os.environ.get('MONGOHQ_URL', None)
            or os.environ.get('MONGOLAB_URI', None)
        )
        # Use app config for DATABASE_URL if no env var from above override it
        config['DATABASE_URL'] = get_config('DATABASE_URL', default=database_url, type=str, config=config)
        config['DATABASE_NAME'] = get_config('DATABASE_NAME', default=None, type=str, config=config)

        config['AUTH_REQUIRED'] = get_config('AUTH_REQUIRED', default=None, type=bool, config=config)
        config['AUTH_PROVIDER'] = get_config('AUTH_PROVIDER', default=None, type=str, config=config)
        config['ADMIN_USERS'] = get_config('ADMIN_USERS', default=[], type=list, config=config)
        config['SIGNUP_ENABLED'] = get_config('SIGNUP_ENABLED', default=True, type=bool, config=config)
        config['CUSTOMER_VIEWS'] = get_config('CUSTOMER_VIEWS', default=False, type=bool, config=config)

        config['OAUTH2_CLIENT_ID'] = get_config('OAUTH2_CLIENT_ID', default=None, type=str, config=config)
        config['OAUTH2_CLIENT_SECRET'] = get_config('OAUTH2_CLIENT_SECRET', default=None, type=str, config=config)
        config['ALLOWED_EMAIL_DOMAINS'] = get_config('ALLOWED_EMAIL_DOMAINS', default=[], type=list, config=config)

        config['AZURE_TENANT'] = get_config('AZURE_TENANT', default=None, type=str, config=config)

        config['GITHUB_URL'] = get_config('GITHUB_URL', default=None, type=str, config=config)
        config['ALLOWED_GITHUB_ORGS'] = get_config('ALLOWED_GITHUB_ORGS', default=[], type=list, config=config)

        config['GITLAB_URL'] = get_config('GITLAB_URL', default=None, type=str, config=config)
        if 'ALLOWED_GITLAB_GROUPS' in os.environ:
            config['ALLOWED_OIDC_ROLES'] = get_config('ALLOWED_GITLAB_GROUPS', default=[], type=list, config=config)

        config['KEYCLOAK_URL'] = get_config('KEYCLOAK_URL', default=None, type=str, config=config)
        config['KEYCLOAK_REALM'] = get_config('KEYCLOAK_REALM', default=None, type=str, config=config)
        if 'ALLOWED_KEYCLOAK_ROLES' in os.environ:
            config['ALLOWED_OIDC_ROLES'] = get_config('ALLOWED_KEYCLOAK_ROLES', default=[], type=list, config=config)

        config['OIDC_ISSUER_URL'] = get_config('OIDC_ISSUER_URL', default=None, type=str, config=config)
        config['ALLOWED_OIDC_ROLES'] = get_config('ALLOWED_OIDC_ROLES', default=[], type=list, config=config)

        config['CORS_ORIGINS'] = get_config('CORS_ORIGINS', default=[], type=list, config=config)

        config['MAIL_FROM'] = get_config('MAIL_FROM', default=None, type=str, config=config)
        config['SMTP_PASSWORD'] = get_config('SMTP_PASSWORD', default=None, type=str, config=config)

        config['GOOGLE_TRACKING_ID'] = get_config('GOOGLE_TRACKING_ID', default=None, type=str, config=config)

        config['PLUGINS'] = get_config('PLUGINS', default=[], type=list, config=config)

        # blackout plugin
        config['BLACKOUT_DURATION'] = get_config('BLACKOUT_DURATION', default=None, type=int, config=config)
        config['NOTIFICATION_BLACKOUT'] = get_config('NOTIFICATION_BLACKOUT', default=None, type=bool, config=config)
        config['BLACKOUT_ACCEPT'] = get_config('BLACKOUT_ACCEPT', default=[], type=list, config=config)

        # reject plugin
        config['ORIGIN_BLACKLIST'] = get_config('ORIGIN_BLACKLIST', default=[], type=list, config=config)
        config['ALLOWED_ENVIRONMENTS'] = get_config('ALLOWED_ENVIRONMENTS', default=[], type=list, config=config)

        # Runtime config check
        if config['CUSTOMER_VIEWS'] and not config['AUTH_REQUIRED']:
            raise RuntimeError('Must enable authentication to use customer views')

        if config['CUSTOMER_VIEWS'] and not config['ADMIN_USERS']:
            raise RuntimeError('Customer views is enabled but there are no admin users')

        return config


def get_config(key, default=None, type=None, **kwargs):

    if key in os.environ:
        rv = os.environ[key]
        if type == bool:
            return rv.lower() in ['yes', 'on', 'true', 't', '1']
        elif type == list:
            return rv.split(',')
        elif type is not None:
            try:
                rv = type(rv)
            except ValueError:
                rv = default
        return rv

    try:
        rv = kwargs['config'].get(key, default)
    except KeyError:
        rv = default
    return rv
