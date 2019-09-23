import os
from flask import Flask
from voluptuous import Schema, Url, Email
import logging
import ast


LOG = logging.getLogger('alerta.config')


class Validator:
    def __init__(self):
        self.string_validator = Schema(str)
        self.integer_validator = Schema(int)
        self.list_validator = Schema(list)
        self.dict_validator = Schema(dict)
        self.url_validator = Schema(Url())
        self.email_validator = Schema(Email())

    @staticmethod
    def boolean_validator(bool):
        if bool == 'True' or bool == 'true' or bool == '1':
            return True
        elif bool == 'False' or bool == 'false' or bool == '0':
            return False
        else:
            return None


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

        if 'DEBUG' in os.environ:
            config['DEBUG'] = Validator.boolean_validator(os.environ['DEBUG'])

            if config['DEBUG'] is True or config['DEBUG'] is False:
                LOG.info('Environment variable DEBUG parsed with value %s', config['DEBUG'])

            else:
                LOG.error('Environment variable DEBUG parsed with value %s', config['DEBUG'])

        if 'BASE_URL' in os.environ:
            try:
                config['BASE_URL'] = Validator().url_validator(
                    os.environ['BASE_URL'])

                LOG.info(
                    'Environment variable BASE_URL parsed with value %s', config['BASE_URL'])

            except Exception as e:
                LOG.error(
                    'Unable to parse environment variable BASE_URL %s', str(e))

        if 'USE_PROXYFIX' in os.environ:
            config['USE_PROXYFIX'] = Validator.boolean_validator(
                os.environ['USE_PROXYFIX'])

            if config['USE_PROXYFIX'] is True or config['USE_PROXYFIX'] is False:
                LOG.info(
                    'Environment variable USE_PROXYFIX parsed with value %s', config['USE_PROXYFIX'])
            else:
                LOG.error(
                    'Unable to parse environment variable USE_PROXYFIX with value %s', config['USE_PROXYFIX'])

        if 'SECRET_KEY' in os.environ:
            try:
                config['SECRET_KEY'] = Validator().string_validator(
                    os.environ['SECRET_KEY'])

                LOG.info(
                    'Environment variable SECRET_KEY parsed with value %s', config['SECRET_KEY'])

            except Exception as e:
                LOG.error(
                    'Unable to parse environment variable SECRET_KEY %s', str(e))

        database_url = (
            os.environ.get('DATABASE_URL', None)
            # The following database settings are deprecated.
            or os.environ.get('MONGO_URI', None)
            or os.environ.get('MONGODB_URI', None)
            or os.environ.get('MONGOHQ_URL', None)
            or os.environ.get('MONGOLAB_URI', None)
        )
        # Use app config for DATABASE_URL if no env var from above override it
        config['DATABASE_URL'] = database_url or config['DATABASE_URL']
        if config['DATABASE_URL']:
            try:
                config['DATABASE_URL'] = Validator().url_validator(
                    os.environ['DATABASE_URL'])

                LOG.info(
                    'Environment variable DATABASE_URL parsed with value %s', config['DATABASE_URL'])

            except Exception as e:
                LOG.error(
                    'Unable to parse environment variable DATABASE_URL %s', str(e))

        if 'DATABASE_NAME' in os.environ:
            config['DATABASE_NAME'] = os.environ['DATABASE_NAME']
            try:
                config['DATABASE_NAME'] = Validator().string_validator(
                    str(os.environ['DATABASE_NAME']))

                LOG.info(
                    'Environment variable DATABASE_NAME parsed with value %s', config['DATABASE_NAME'])

            except Exception as e:
                LOG.error(
                    'Unable to parse environment variable DATABASE_NAME %s', str(e))

        if 'AUTH_REQUIRED' in os.environ:
            config['AUTH_REQUIRED'] = Validator.boolean_validator(
                os.environ['AUTH_REQUIRED'])

            if config['AUTH_REQUIRED'] is True or config['AUTH_REQUIRED'] is False:
                LOG.info(
                    'Environment variable AUTH_REQUIRED parsed with value %s', config['AUTH_REQUIRED'])
            else:
                LOG.error(
                    'Unable to parse environment variable AUTH_REQUIRED with value %s', config['AUTH_REQUIRED'])

        if 'AUTH_PROVIDER' in os.environ:
            try:
                config['AUTH_PROVIDER'] = Validator().string_validator(
                    str(os.environ['AUTH_PROVIDER']))

                LOG.info(
                    'Environment variable AUTH_PROVIDER parsed with value %s', config['AUTH_PROVIDER'])

            except Exception as e:
                LOG.error(
                    'Unable to parse environment variable AUTH_PROVIDER %s', str(e))

        if 'ADMIN_USERS' in os.environ:
            try:
                list_data = ast.literal_eval(os.environ['ADMIN_USERS'])
                valid_list = Validator().list_validator(list_data)
                strSchema = Schema([str])
                config['ADMIN_USERS'] = strSchema(valid_list)

                LOG.info(
                    'Environment variable ADMIN_USERS parsed with value %s', config['ADMIN_USERS'])

            except Exception:
                LOG.error(
                    'Unable to parse environment variable ADMIN_USERS with value %s', config['ADMIN_USERS'])

        if 'SIGNUP_ENABLED' in os.environ:
            config['SIGNUP_ENABLED'] = Validator.boolean_validator(
                os.environ['SIGNUP_ENABLED'])

            if config['SIGNUP_ENABLED'] is True or config['SIGNUP_ENABLED'] is False:
                LOG.info(
                    'Environment variable SIGNUP_ENABLED parsed with value %s', config['SIGNUP_ENABLED'])
            else:
                LOG.error(
                    'Unable to parse environment variable SIGNUP_ENABLED with value %s', config['SIGNUP_ENABLED'])

        if 'CUSTOMER_VIEWS' in os.environ:
            config['CUSTOMER_VIEWS'] = Validator.boolean_validator(
                os.environ['CUSTOMER_VIEWS'])

            if config['CUSTOMER_VIEWS'] is True or config['CUSTOMER_VIEWS'] is False:
                LOG.info(
                    'Environment variable CUSTOMER_VIEWS parsed with value %s', config['CUSTOMER_VIEWS'])
            else:
                LOG.error(
                    'Unable to parse environment variable CUSTOMER_VIEWS with value %s', config['CUSTOMER_VIEWS'])

        if 'OAUTH2_CLIENT_ID' in os.environ:
            try:
                config['OAUTH2_CLIENT_ID'] = Validator().string_validator(
                    os.environ['OAUTH2_CLIENT_ID'])

                LOG.info(
                    'Environment variable OAUTH2_CLIENT_ID parsed with value %s', config['OAUTH2_CLIENT_ID'])

            except Exception as e:
                LOG.error(
                    'Unable to parse environment variable OAUTH2_CLIENT_ID %s', str(e))

        if 'OAUTH2_CLIENT_SECRET' in os.environ:
            try:
                config['OAUTH2_CLIENT_SECRET'] = Validator().string_validator(
                    os.environ['OAUTH2_CLIENT_SECRET'])

                LOG.info('Environment variable OAUTH2_CLIENT_SECRET parsed with value %s',
                            config['OAUTH2_CLIENT_SECRET'])

            except Exception as e:
                LOG.error(
                    'Unable to parse environment variable OAUTH2_CLIENT_SECRET %s', str(e))

        if 'ALLOWED_EMAIL_DOMAINS' in os.environ:
            try:
                list_data = ast.literal_eval(
                    os.environ['ALLOWED_EMAIL_DOMAINS'])
                valid_list = Validator().list_validator(list_data)
                domainSchema = Schema([str])
                config['ALLOWED_EMAIL_DOMAINS'] = domainSchema(valid_list)

                LOG.info('Environment variable ALLOWED_EMAIL_DOMAINS parsed with value %s',
                            config['ALLOWED_EMAIL_DOMAINS'])

            except Exception:
                LOG.error(
                    'Unable to parse environment variable ALLOWED_EMAIL_DOMAINS with value %s', config['ALLOWED_EMAIL_DOMAINS'])

        if 'AZURE_TENANT' in os.environ:
            try:
                config['AZURE_TENANT'] = Validator().string_validator(
                    os.environ['AZURE_TENANT'])

                LOG.info(
                    'Environment variable AZURE_TENANT parsed with value %s', config['AZURE_TENANT'])

            except Exception as e:
                LOG.error(
                    'Unable to parse environment variable AZURE_TENANT %s', str(e))

        if 'GITHUB_URL' in os.environ:
            try:
                config['GITHUB_URL'] = Validator().url_validator(
                    os.environ['GITHUB_URL'])

                LOG.info(
                    'Environment variable GITHUB_URL parsed with value %s', config['GITHUB_URL'])

            except Exception as e:
                LOG.error(
                    'Unable to parse environment variable GITHUB_URL %s', str(e))

        if 'ALLOWED_GITHUB_ORGS' in os.environ:
            try:
                list_data = ast.literal_eval(os.environ['ALLOWED_GITHUB_ORGS'])
                valid_list = Validator().list_validator(list_data)
                strSchema = Schema([str])
                config['ALLOWED_GITHUB_ORGS'] = strSchema(valid_list)

                LOG.info(
                    'Environment variable ALLOWED_GITHUB_ORGS parsed with value %s', config['ALLOWED_GITHUB_ORGS'])

            except Exception:
                LOG.error(
                    'Unable to parse environment variable ALLOWED_GITHUB_ORGS with value %s', config['ALLOWED_GITHUB_ORGS'])

        if 'GITLAB_URL' in os.environ:
            try:
                config['GITLAB_URL'] = Validator().url_validator(
                    os.environ['GITLAB_URL'])

                LOG.info(
                    'Environment variable GITLAB_URL parsed with value %s', config['GITLAB_URL'])

            except Exception as e:
                LOG.error(
                    'Unable to parse environment variable GITLAB_URL %s', str(e))

        if 'ALLOWED_GITLAB_GROUPS' in os.environ:
            try:
                list_data = ast.literal_eval(os.environ['ALLOWED_GITLAB_GROUPS'])
                valid_list = Validator().list_validator(list_data)
                strSchema = Schema([str])
                config['ALLOWED_OIDC_ROLES'] = strSchema(valid_list)

                LOG.info(
                    'Environment variable ALLOWED_GITLAB_GROUPS parsed with value %s', config['ALLOWED_OIDC_ROLES'])

            except Exception:
                LOG.error(
                    'Unable to parse environment variable ALLOWED_GITLAB_GROUPS with value %s', config['ALLOWED_OIDC_ROLES'])

        if 'KEYCLOAK_URL' in os.environ:
            try:
                config['KEYCLOAK_URL'] = Validator().url_validator(
                    os.environ['KEYCLOAK_URL'])

                LOG.info(
                    'Environment variable KEYCLOAK_URL parsed with value %s', config['KEYCLOAK_URL'])

            except Exception as e:
                LOG.error(
                    'Unable to parse environment variable KEYCLOAK_URL %s', str(e))

        if 'KEYCLOAK_REALM' in os.environ:
            try:
                config['KEYCLOAK_REALM'] = Validator().string_validator(
                    os.environ['KEYCLOAK_REALM'])

                LOG.info(
                    'Environment variable KEYCLOAK_REALM parsed with value %s', config['KEYCLOAK_REALM'])

            except Exception as e:
                LOG.error(
                    'Unable to parse environment variable KEYCLOAK_REALM %s', str(e))

        if 'ALLOWED_KEYCLOAK_ROLES' in os.environ:
            try:
                list_data = ast.literal_eval(os.environ['ALLOWED_KEYCLOAK_ROLES'])
                valid_list = Validator().list_validator(list_data)
                strSchema = Schema([str])
                config['ALLOWED_OIDC_ROLES'] = strSchema(valid_list)

                LOG.info(
                    'Environment variable ALLOWED_KEYCLOAK_ROLES parsed with value %s', config['ALLOWED_KEYCLOAK_ROLES'])

            except Exception:
                LOG.error(
                    'Unable to parse environment variable ALLOWED_KEYCLOAK_ROLES with value %s', config['ALLOWED_KEYCLOAK_ROLES'])

        if 'OIDC_ISSUER_URL' in os.environ:
            try:
                config['OIDC_ISSUER_URL'] = Validator().url_validator(
                    os.environ['OIDC_ISSUER_URL'])

                LOG.info(
                    'Environment variable OIDC_ISSUER_URL parsed with value %s', config['OIDC_ISSUER_URL'])

            except Exception as e:
                LOG.error(
                    'Unable to parse environment variable OIDC_ISSUER_URL %s', str(e))

        if 'ALLOWED_OIDC_ROLES' in os.environ:
            try:
                list_data = ast.literal_eval(os.environ['ALLOWED_OIDC_ROLES'])
                valid_list = Validator().list_validator(list_data)
                strSchema = Schema([str])
                config['ALLOWED_OIDC_ROLES'] = strSchema(valid_list)

                LOG.info(
                    'Environment variable ALLOWED_OIDC_ROLES parsed with value %s', config['ALLOWED_OIDC_ROLES'])

            except Exception:
                LOG.error(
                    'Unable to parse environment variable ALLOWED_OIDC_ROLES with value %s', config['ALLOWED_OIDC_ROLES'])

        if 'CORS_ORIGINS' in os.environ:
            try:
                list_data = ast.literal_eval(os.environ['CORS_ORIGINS'])
                valid_list = Validator().list_validator(list_data)
                urlSchema = Schema([Url()])
                config['CORS_ORIGINS'] = urlSchema(valid_list)

                LOG.info(
                    'Environment variable CORS_ORIGINS parsed with value %s', config['CORS_ORIGINS'])

            except Exception:
                LOG.error(
                    'Unable to parse environment variable CORS_ORIGINS with value %s', config['CORS_ORIGINS'])

        if 'MAIL_FROM' in os.environ:
            try:
                config['MAIL_FROM'] = Validator().email_validator(
                    os.environ['MAIL_FROM'])

                LOG.info(
                    'Environment variable MAIL_FROM parsed with value %s', config['MAIL_FROM'])

            except Exception as e:
                LOG.error(
                    'Unable to parse environment variable MAIL_FROM %s', str(e))

        if 'SMTP_PASSWORD' in os.environ:
            try:
                config['SMTP_PASSWORD'] = Validator().string_validator(
                    os.environ['SMTP_PASSWORD'])

                LOG.info(
                    'Environment variable SMTP_PASSWORD parsed with value %s', config['SMTP_PASSWORD'])

            except Exception as e:
                LOG.error(
                    'Unable to parse environment variable SMTP_PASSWORD %s', str(e))

        if 'GOOGLE_TRACKING_ID' in os.environ:
            try:
                config['GOOGLE_TRACKING_ID'] = Validator().string_validator(
                    os.environ['GOOGLE_TRACKING_ID'])

                LOG.info(
                    'Environment variable GOOGLE_TRACKING_ID parsed with value %s', config['GOOGLE_TRACKING_ID'])

            except Exception as e:
                LOG.error(
                    'Unable to parse environment variable GOOGLE_TRACKING_ID %s', str(e))

        if 'PLUGINS' in os.environ:
            try:
                list_data = ast.literal_eval(os.environ['PLUGINS'])
                valid_list = Validator().list_validator(list_data)
                urlSchema = Schema([str])
                config['PLUGINS'] = urlSchema(valid_list)

                LOG.info(
                    'Environment variable PLUGINS parsed with value %s', config['PLUGINS'])

            except Exception:
                LOG.error(
                    'Unable to parse environment variable PLUGINS with value %s', config['PLUGINS'])

        if 'ALERT_TIMEOUT' in os.environ:
            try:
                config['ALERT_TIMEOUT'] = Validator().integer_validator(
                    int(os.environ['ALERT_TIMEOUT']))

                LOG.info('Environment variable ALERT_TIMEOUT parsed with value %s', str(
                    config['ALERT_TIMEOUT']))

            except Exception as e:
                LOG.error(
                    'Unable to parse environment variable ALERT_TIMEOUT %s', str(e))

        if 'HEARTBEAT_TIMEOUT' in os.environ:
            try:
                config['HEARTBEAT_TIMEOUT'] = Validator().integer_validator(
                    int(os.environ['HEARTBEAT_TIMEOUT']))

                LOG.info('Environment variable HEARTBEAT_TIMEOUT parsed with value %s', str(
                    config['HEARTBEAT_TIMEOUT']))

            except Exception as e:
                LOG.error(
                    'Unable to parse environment variable HEARTBEAT_TIMEOUT %s', str(e))

        if 'API_KEY_EXPIRE_DAYS' in os.environ:
            try:
                config['API_KEY_EXPIRE_DAYS'] = Validator().integer_validator(
                    int(os.environ['API_KEY_EXPIRE_DAYS']))

                LOG.info('Environment variable API_KEY_EXPIRE_DAYS parsed with value %s', str(
                    config['API_KEY_EXPIRE_DAYS']))

            except Exception as e:
                LOG.error(
                    'Unable to parse environment variable API_KEY_EXPIRE_DAYS %s', str(e))

        # Runtime config check
        if config['CUSTOMER_VIEWS'] and not config['AUTH_REQUIRED']:
            raise RuntimeError(
                'Must enable authentication to use customer views')

        if config['CUSTOMER_VIEWS'] and not config['ADMIN_USERS']:
            raise RuntimeError(
                'Customer views is enabled but there are no admin users')

        return config
