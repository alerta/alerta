import ast
import logging
import os
from typing import List, Tuple

from flask import Flask
from voluptuous import Email, MultipleInvalid, Schema, TypeInvalid, Url

LOG = logging.getLogger('alerta.config')


class Validate:
    def __init__(self):
        self.string_validator = Schema(str)
        self.integer_validator = Schema(int)
        self.list_string_validator = Schema([str])
        self.list_integer_validator = Schema([int])
        self.list_url_validator = Schema([Url(str)])
        self.url_validator = Schema(Url(str))
        self.email_validator = Schema(Email(str))

    def validate_boolean(self, boolean_string: str) -> bool:
        if boolean_string.lower() in ['true', '1', 'yes', 'y', 'on']:
            variable_value = True
        elif boolean_string.lower() in ['false', '0', 'no', 'n', 'off']:
            variable_value = False
        else:
            raise ValueError('Could not parse boolean from environment variable')

        return variable_value

    def validate_url(self, url_string: str) -> Tuple[str, List[str]]:
        try:
            if isinstance(url_string, list):
                variable_value = []
                for item in url_string:
                    self.url_validator(item)
                variable_value = url_string

            else:
                variable_value = self.url_validator(url_string)

            return variable_value

        except (TypeInvalid, MultipleInvalid) as e:
            raise RuntimeError('Unable to validate environment variable %s' % (e))

    def validate_string(self, string_string: str) -> str:
        try:
            variable_value = self.string_validator(string_string)

            return variable_value

        except (TypeInvalid, MultipleInvalid) as e:
            raise RuntimeError('Unable to validate environment variable %s' % (e))

    def validate_email(self, email_string: str) -> str:
        try:
            variable_value = self.email_validator(email_string)

            return variable_value

        except (TypeInvalid, MultipleInvalid) as e:
            raise RuntimeError('Unable to validate environment variable %s' % (e))

    def validate_integer(self, integer_string: str) -> int:
        try:
            variable_value = self.integer_validator(int(integer_string))

            return variable_value

        except (TypeInvalid, MultipleInvalid) as e:
            raise RuntimeError('Unable to validate environment variable %s' % (e))

    def validate_list(self, list_string: str, list_type: str) -> List:
        try:
            list_data = ast.literal_eval(list_string)

            if list_type == 'string':
                variable_value = self.list_string_validator(list_data)

            elif list_type == 'url':
                variable_value = self.list_url_validator(list_data)

            elif list_type == 'integer':
                variable_value = self.list_integer_validator(list_data)

            return variable_value
        except (ValueError, TypeInvalid, MultipleInvalid, SyntaxError):
            try:
                # For backward compatibility
                list_data = list_string.split(',')

                if list_type == 'string':
                    variable_value = self.list_string_validator(list_data)

                elif list_type == 'url':
                    variable_value = self.list_url_validator(list_data)

                elif list_type == 'integer':
                    numbers = [int(x) for x in list_data]
                    variable_value = self.list_integer_validator(numbers)

                return variable_value
            except (TypeInvalid, MultipleInvalid) as e:
                raise RuntimeError('Unable to validate environment variable %s' % (e))


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
        valid = Validate()
        from flask import Config
        config = Config('/')

        config.from_object('alerta.settings')
        config.from_pyfile('/etc/alertad.conf', silent=True)
        config.from_envvar('ALERTA_SVR_CONF_FILE', silent=True)

        if 'DEBUG' in os.environ:
            config['DEBUG'] = valid.validate_boolean(os.environ['DEBUG'])

        if 'BASE_URL' in os.environ:
            config['BASE_URL'] = valid.validate_url(os.environ['BASE_URL'])

        if 'USE_PROXYFIX' in os.environ:
            config['USE_PROXYFIX'] = valid.validate_boolean(os.environ['USE_PROXYFIX'])

        if 'SECRET_KEY' in os.environ:
            config['SECRET_KEY'] = valid.validate_string(os.environ['SECRET_KEY'])

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
            config['DATABASE_URL'] = valid.validate_url(os.environ['DATABASE_URL'])

        if 'DATABASE_NAME' in os.environ:
            config['DATABASE_NAME'] = valid.validate_string(os.environ['DATABASE_NAME'])

        if 'AUTH_REQUIRED' in os.environ:
            config['AUTH_REQUIRED'] = valid.validate_boolean(os.environ['AUTH_REQUIRED'])

        if 'AUTH_PROVIDER' in os.environ:
            config['AUTH_PROVIDER'] = valid.validate_string(os.environ['AUTH_PROVIDER'])

        if 'ADMIN_USERS' in os.environ:
            config['ADMIN_USERS'] = valid.validate_list(os.environ['ADMIN_USERS'], 'string')

        if 'SIGNUP_ENABLED' in os.environ:
            config['SIGNUP_ENABLED'] = valid.validate_boolean(os.environ['SIGNUP_ENABLED'])

        if 'CUSTOMER_VIEWS' in os.environ:
            config['CUSTOMER_VIEWS'] = valid.validate_boolean(os.environ['CUSTOMER_VIEWS'])

        if 'OAUTH2_CLIENT_ID' in os.environ:
            config['OAUTH2_CLIENT_ID'] = valid.validate_string(os.environ['OAUTH2_CLIENT_ID'])

        if 'OAUTH2_CLIENT_SECRET' in os.environ:
            config['OAUTH2_CLIENT_SECRET'] = valid.validate_string(os.environ['OAUTH2_CLIENT_SECRET'])

        if 'ALLOWED_EMAIL_DOMAINS' in os.environ:
            config['ALLOWED_EMAIL_DOMAINS'] = valid.validate_list(os.environ['ALLOWED_EMAIL_DOMAINS'], 'string')

        if 'AZURE_TENANT' in os.environ:
            config['AZURE_TENANT'] = valid.validate_string(os.environ['AZURE_TENANT'])

        if 'GITHUB_URL' in os.environ:
            config['GITHUB_URL'] = valid.validate_url(os.environ['GITHUB_URL'])

        if 'ALLOWED_GITHUB_ORGS' in os.environ:
            config['ALLOWED_GITHUB_ORGS'] = valid.validate_list(os.environ['ALLOWED_GITHUB_ORGS'], 'string')

        if 'GITLAB_URL' in os.environ:
            config['GITLAB_URL'] = valid.validate_url(os.environ['GITLAB_URL'])

        if 'ALLOWED_GITLAB_GROUPS' in os.environ:
            config['ALLOWED_OIDC_ROLES'] = valid.validate_list(os.environ['ALLOWED_GITLAB_GROUPS'], 'string')

        if 'KEYCLOAK_URL' in os.environ:
            config['KEYCLOAK_URL'] = valid.validate_url(os.environ['KEYCLOAK_URL'])

        if 'KEYCLOAK_REALM' in os.environ:
            config['KEYCLOAK_REALM'] = valid.validate_string(os.environ['KEYCLOAK_REALM'])

        if 'ALLOWED_KEYCLOAK_ROLES' in os.environ:
            config['ALLOWED_OIDC_ROLES'] = valid.validate_list(os.environ['ALLOWED_KEYCLOAK_ROLES'], 'string')

        if 'OIDC_ISSUER_URL' in os.environ:
            config['OIDC_ISSUER_URL'] = valid.validate_url(os.environ['OIDC_ISSUER_URL'])

        if 'ALLOWED_OIDC_ROLES' in os.environ:
            config['ALLOWED_OIDC_ROLES'] = valid.validate_list(os.environ['ALLOWED_OIDC_ROLES'], 'string')

        if 'CORS_ORIGINS' in os.environ:
            config['CORS_ORIGINS'] = valid.validate_list(os.environ['CORS_ORIGINS'], 'url')

        if 'MAIL_FROM' in os.environ:
            config['MAIL_FROM'] = valid.validate_email(os.environ['MAIL_FROM'])

        if 'SMTP_PASSWORD' in os.environ:
            config['SMTP_PASSWORD'] = valid.validate_string(os.environ['SMTP_PASSWORD'])

        if 'GOOGLE_TRACKING_ID' in os.environ:
            config['GOOGLE_TRACKING_ID'] = valid.validate_string(os.environ['GOOGLE_TRACKING_ID'])

        if 'PLUGINS' in os.environ:
            config['PLUGINS'] = valid.validate_list(os.environ['PLUGINS'], 'string')

        if 'ALERT_TIMEOUT' in os.environ:
            config['ALERT_TIMEOUT'] = valid.validate_integer(os.environ['ALERT_TIMEOUT'])

        if 'HEARTBEAT_TIMEOUT' in os.environ:
            config['HEARTBEAT_TIMEOUT'] = valid.validate_integer(os.environ['HEARTBEAT_TIMEOUT'])

        if 'API_KEY_EXPIRE_DAYS' in os.environ:
            config['API_KEY_EXPIRE_DAYS'] = valid.validate_integer(os.environ['API_KEY_EXPIRE_DAYS'])

        # Runtime config check
        if config['CUSTOMER_VIEWS'] and not config['AUTH_REQUIRED']:
            raise RuntimeError('Must enable authentication to use customer views')

        if config['CUSTOMER_VIEWS'] and not config['ADMIN_USERS']:
            raise RuntimeError('Customer views is enabled but there are no admin users')

        return config
