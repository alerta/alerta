import os
from flask import Flask
from voluptuous import Schema, Url, Email
import logging
import ast


LOG = logging.getLogger('alerta.config')


class Validate:
    def __init__(self):
        self.string_validator = Schema(str)
        self.integer_validator = Schema(int)
        self.list_validator = Schema(list)
        self.url_validator = Schema(Url())
        self.email_validator = Schema(Email())

    def get_variable(self, variable_name):
        environment_string = os.environ[variable_name]

        return environment_string

    def validate_boolean(self, variable_name, boolean_string):
        if boolean_string == 'True' or boolean_string == 'true' or boolean_string == '1':
            variable_value = True
            LOG.info(
                f'Environment variable {variable_name} parsed with value {variable_value}')

        elif boolean_string == 'False' or boolean_string == 'false' or boolean_string == '0':
            variable_value = False
            LOG.info(
                f'Environment variable {variable_name} parsed with value {variable_value}')

        else:
            variable_value = False
            LOG.error(
                f'Environment variable {variable_name} parsed with value {variable_value}')

        return variable_value

    def validate_url(self, variable_name, url_string):
        try:
            if isinstance(url_string, list):
                variable_value = []
                for item in url_string:
                    self.url_validator(item)
                variable_value = url_string

            else:
                variable_value = self.url_validator(url_string)

            LOG.info(
                f'Environment variable {variable_name} parsed with value {variable_value}')
            return variable_value

        except Exception as e:
            LOG.error(
                f'Unable to parse environment variable {variable_name} {str(e)}')
            return None

    def validate_string(self, variable_name, string_string):
        try:
            if isinstance(string_string, list):
                variable_value = []
                for item in string_string:
                    self.string_validator(item)
                variable_value = string_string

            else:
                variable_value = self.string_validator(string_string)

            LOG.info(
                f'Environment variable {variable_name} parsed with value {variable_value}')
            return variable_value

        except Exception as e:
            LOG.error(
                f'Unable to parse environment variable {variable_name} {str(e)}')
            return None

    def validate_email(self, variable_name, email_string):
        try:
            variable_value = self.email_validator(email_string)

            LOG.info(
                f'Environment variable {variable_name} parsed with value {variable_value}')
            return variable_value

        except Exception as e:
            LOG.error(
                f'Unable to parse environment variable {variable_name} {str(e)}')
            return None

    def validate_integer(self, variable_name, integer_string):
        try:
            variable_value = self.integer_validator(int(integer_string))

            LOG.info(
                f'Environment variable {variable_name} parsed with value {variable_value}')
            return variable_value

        except Exception as e:
            LOG.error(
                f'Unable to parse environment variable {variable_name} {str(e)}')
            return None

    def validate_list(self, variable_name, list_string):
        try:
            # For backward compatibility
            if '[' in list_string and ']' in list_string:

                list_data = ast.literal_eval(list_string)
                variable_value = self.list_validator(list_data)

            else:
                list_data = list_string.split(',')
                variable_value = self.list_validator(list_data)

            LOG.info(
                f'Environment variable {variable_name} parsed with value {variable_value}')
            return variable_value

        except Exception as e:
            LOG.error(
                f'Unable to parse environment variable {variable_name} {str(e)}')
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
        Valid = Validate()
        from flask import Config
        config = Config('/')

        config.from_object('alerta.settings')
        config.from_pyfile('/etc/alertad.conf', silent=True)
        config.from_envvar('ALERTA_SVR_CONF_FILE', silent=True)

        if 'DEBUG' in os.environ:
            config['DEBUG'] = Valid.validate_boolean(
                'DEBUG', Valid.get_variable('DEBUG'))

        if 'BASE_URL' in os.environ:
            config['BASE_URL'] = Valid.validate_url(
                'BASE_URL', Valid.get_variable('BASE_URL'))

        if 'USE_PROXYFIX' in os.environ:
            config['USE_PROXYFIX'] = Valid.validate_boolean(
                'USE_PROXYFIX', Valid.get_variable('USE_PROXYFIX'))

        if 'SECRET_KEY' in os.environ:
            config['SECRET_KEY'] = Valid.validate_string(
                'SECRET_KEY', Valid.get_variable('SECRET_KEY'))

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

        if config['DATABASE_URL'] in os.environ:
            config['DATABASE_URL'] = Valid.validate_url(
                'DATABASE_URL', Valid.get_variable('DATABASE_URL'))

        if 'DATABASE_NAME' in os.environ:
            config['DATABASE_NAME'] = Valid.validate_string(
                'DATABASE_NAME', Valid.get_variable('DATABASE_NAME'))

        if 'AUTH_REQUIRED' in os.environ:
            config['AUTH_REQUIRED'] = Valid.validate_boolean(
                'AUTH_REQUIRED', Valid.get_variable('AUTH_REQUIRED'))

        if 'AUTH_PROVIDER' in os.environ:
            config['AUTH_PROVIDER'] = Valid.validate_string(
                'AUTH_PROVIDER', Valid.get_variable('AUTH_PROVIDER'))

        if 'ADMIN_USERS' in os.environ:
            list = Valid.validate_list(
                'ADMIN_USERS', Valid.get_variable('ADMIN_USERS'))
            config['ADMIN_USERS'] = Valid.validate_string(
                'ADMIN_USERS', list)

        if 'SIGNUP_ENABLED' in os.environ:
            config['SIGNUP_ENABLED'] = Valid.validate_boolean(
                'SIGNUP_ENABLED', Valid.get_variable('SIGNUP_ENABLED'))

        if 'CUSTOMER_VIEWS' in os.environ:
            config['CUSTOMER_VIEWS'] = Valid.validate_boolean(
                'CUSTOMER_VIEWS', Valid.get_variable('CUSTOMER_VIEWS'))

        if 'OAUTH2_CLIENT_ID' in os.environ:
            config['OAUTH2_CLIENT_ID'] = Valid.validate_string(
                'OAUTH2_CLIENT_ID', Valid.get_variable('OAUTH2_CLIENT_ID'))

        if 'OAUTH2_CLIENT_SECRET' in os.environ:
            config['OAUTH2_CLIENT_SECRET'] = Valid.validate_string(
                'OAUTH2_CLIENT_SECRET', Valid.get_variable('OAUTH2_CLIENT_SECRET'))

        if 'ALLOWED_EMAIL_DOMAINS' in os.environ:
            list = Valid.validate_list(
                'ALLOWED_EMAIL_DOMAINS', Valid.get_variable('ALLOWED_EMAIL_DOMAINS'))
            config['ALLOWED_EMAIL_DOMAINS'] = Valid.validate_string(
                'ALLOWED_EMAIL_DOMAINS', list)

        if 'AZURE_TENANT' in os.environ:
            config['AZURE_TENANT'] = Valid.validate_string(
                'AZURE_TENANT', Valid.get_variable('AZURE_TENANT'))

        if 'GITHUB_URL' in os.environ:
            config['GITHUB_URL'] = Valid.validate_url(
                'GITHUB_URL', Valid.get_variable('GITHUB_URL'))

        if 'ALLOWED_GITHUB_ORGS' in os.environ:
            list = Valid.validate_list(
                'ALLOWED_GITHUB_ORGS', Valid.get_variable('ALLOWED_GITHUB_ORGS'))
            config['ALLOWED_GITHUB_ORGS'] = Valid.validate_string(
                'ALLOWED_GITHUB_ORGS', list)

        if 'GITLAB_URL' in os.environ:
            config['GITLAB_URL'] = Valid.validate_url(
                'GITLAB_URL', Valid.get_variable('GITLAB_URL'))

        if 'ALLOWED_GITLAB_GROUPS' in os.environ:
            list = Valid.validate_list(
                'ALLOWED_GITLAB_GROUPS', Valid.get_variable('ALLOWED_GITLAB_GROUPS'))
            config['ALLOWED_OIDC_ROLES'] = Valid.validate_string(
                'ALLOWED_GITLAB_GROUPS', list)

        if 'KEYCLOAK_URL' in os.environ:
            config['KEYCLOAK_URL'] = Valid.validate_url(
                'KEYCLOAK_URL', Valid.get_variable('KEYCLOAK_URL'))

        if 'KEYCLOAK_REALM' in os.environ:
            config['KEYCLOAK_REALM'] = Valid.validate_string(
                'KEYCLOAK_REALM', Valid.get_variable('KEYCLOAK_REALM'))

        if 'ALLOWED_KEYCLOAK_ROLES' in os.environ:
            list = Valid.validate_list(
                'ALLOWED_KEYCLOAK_ROLES', Valid.get_variable('ALLOWED_KEYCLOAK_ROLES'))
            config['ALLOWED_OIDC_ROLES'] = Valid.validate_string(
                'ALLOWED_KEYCLOAK_ROLES', list)

        if 'OIDC_ISSUER_URL' in os.environ:
            config['OIDC_ISSUER_URL'] = Valid.validate_url(
                'OIDC_ISSUER_URL', Valid.get_variable('OIDC_ISSUER_URL'))

        if 'ALLOWED_OIDC_ROLES' in os.environ:
            list = Valid.validate_list(
                'ALLOWED_OIDC_ROLES', Valid.get_variable('ALLOWED_OIDC_ROLES'))
            config['ALLOWED_OIDC_ROLES'] = Valid.validate_string(
                'ALLOWED_OIDC_ROLES', list)

        if 'CORS_ORIGINS' in os.environ:
            list = Valid.validate_list(
                'CORS_ORIGINS', Valid.get_variable('CORS_ORIGINS'))
            config['CORS_ORIGINS'] = Valid.validate_url(
                'CORS_ORIGINS', list)

        if 'MAIL_FROM' in os.environ:
            config['MAIL_FROM'] = Valid.validate_email(
                'MAIL_FROM', Valid.get_variable('MAIL_FROM'))

        if 'SMTP_PASSWORD' in os.environ:
            config['SMTP_PASSWORD'] = Valid.validate_string(
                'SMTP_PASSWORD', Valid.get_variable('SMTP_PASSWORD'))

        if 'GOOGLE_TRACKING_ID' in os.environ:
            config['GOOGLE_TRACKING_ID'] = Valid.validate_string(
                'GOOGLE_TRACKING_ID', Valid.get_variable('GOOGLE_TRACKING_ID'))

        if 'PLUGINS' in os.environ:
            list = Valid.validate_list(
                'PLUGINS', Valid.get_variable('PLUGINS'))
            config['PLUGINS'] = Valid.validate_string(
                'PLUGINS', list)

        if 'ALERT_TIMEOUT' in os.environ:
            config['ALERT_TIMEOUT'] = Valid.validate_integer(
                'ALERT_TIMEOUT', Valid.get_variable('ALERT_TIMEOUT'))

        if 'HEARTBEAT_TIMEOUT' in os.environ:
            config['HEARTBEAT_TIMEOUT'] = Valid.validate_integer(
                'HEARTBEAT_TIMEOUT', Valid.get_variable('HEARTBEAT_TIMEOUT'))

        if 'API_KEY_EXPIRE_DAYS' in os.environ:
            config['API_KEY_EXPIRE_DAYS'] = Valid.validate_integer(
                'API_KEY_EXPIRE_DAYS', Valid.get_variable('API_KEY_EXPIRE_DAYS'))

        # Runtime config check
        if config['CUSTOMER_VIEWS'] and not config['AUTH_REQUIRED']:
            raise RuntimeError(
                'Must enable authentication to use customer views')

        if config['CUSTOMER_VIEWS'] and not config['ADMIN_USERS']:
            raise RuntimeError(
                'Customer views is enabled but there are no admin users')

        return config
