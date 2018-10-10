
import logging
import os
from logging import Handler  # noqa
from logging.handlers import RotatingFileHandler

from flask import Flask
from flask.logging import default_handler, wsgi_errors_stream


class Config:

    def __init__(self, app: Flask=None) -> None:
        self.app = None
        if app:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        config = self.get_user_config()
        app.config.update(config)
        self.setup_logging(app)

    @staticmethod
    def get_user_config():
        from flask import Config
        config = Config('/')

        config.from_object('alerta.settings')
        config.from_pyfile('/etc/alertad.conf', silent=True)
        config.from_envvar('ALERTA_SVR_CONF_FILE', silent=True)

        if 'DEBUG' in os.environ:
            config['DEBUG'] = True

        if 'BASE_URL' in os.environ:
            config['BASE_URL'] = os.environ['BASE_URL']

        if 'SECRET_KEY' in os.environ:
            config['SECRET_KEY'] = os.environ['SECRET_KEY']

        database_url = (
            os.environ.get('DATABASE_URL', None) or
            # The following database settings are deprecated.
            os.environ.get('MONGO_URI', None) or
            os.environ.get('MONGODB_URI', None) or
            os.environ.get('MONGOHQ_URL', None) or
            os.environ.get('MONGOLAB_URI', None)
        )
        # Use app config for DATABASE_URL if no env var from above override it
        config['DATABASE_URL'] = database_url or config['DATABASE_URL']

        if 'DATABASE_NAME' in os.environ:
            config['DATABASE_NAME'] = os.environ['DATABASE_NAME']

        if 'AUTH_REQUIRED' in os.environ:
            config['AUTH_REQUIRED'] = True if os.environ['AUTH_REQUIRED'] == 'True' else False

        if 'AUTH_PROVIDER' in os.environ:
            config['AUTH_PROVIDER'] = os.environ['AUTH_PROVIDER']

        if 'ADMIN_USERS' in os.environ:
            config['ADMIN_USERS'] = os.environ['ADMIN_USERS'].split(',')

        if 'CUSTOMER_VIEWS' in os.environ:
            config['CUSTOMER_VIEWS'] = True if os.environ['CUSTOMER_VIEWS'] == 'True' else False

        if 'OAUTH2_CLIENT_ID' in os.environ:
            config['OAUTH2_CLIENT_ID'] = os.environ['OAUTH2_CLIENT_ID']

        if 'OAUTH2_CLIENT_SECRET' in os.environ:
            config['OAUTH2_CLIENT_SECRET'] = os.environ['OAUTH2_CLIENT_SECRET']

        if 'ALLOWED_EMAIL_DOMAINS' in os.environ:
            config['ALLOWED_EMAIL_DOMAINS'] = os.environ['ALLOWED_EMAIL_DOMAINS'].split(',')

        if 'GITHUB_URL' in os.environ:
            config['GITHUB_URL'] = os.environ['GITHUB_URL']

        if 'ALLOWED_GITHUB_ORGS' in os.environ:
            config['ALLOWED_GITHUB_ORGS'] = os.environ['ALLOWED_GITHUB_ORGS'].split(',')

        if 'GITLAB_URL' in os.environ:
            config['GITLAB_URL'] = os.environ['GITLAB_URL']

        if 'ALLOWED_GITLAB_GROUPS' in os.environ:
            config['ALLOWED_GITLAB_GROUPS'] = os.environ['ALLOWED_GITLAB_GROUPS'].split(',')

        if 'KEYCLOAK_URL' in os.environ:
            config['KEYCLOAK_URL'] = os.environ['KEYCLOAK_URL']

        if 'KEYCLOAK_REALM' in os.environ:
            config['KEYCLOAK_REALM'] = os.environ['KEYCLOAK_REALM']

        if 'ALLOWED_KEYCLOAK_ROLES' in os.environ:
            config['ALLOWED_KEYCLOAK_ROLES'] = os.environ['ALLOWED_KEYCLOAK_ROLES'].split(',')

        if 'PINGFEDERATE_OPENID_ACCESS_TOKEN_URL' in os.environ:
            config['PINGFEDERATE_OPENID_ACCESS_TOKEN_URL'] = os.environ['PINGFEDERATE_OPENID_ACCESS_TOKEN_URL'].split(
                ',')

        if 'PINGFEDERATE_OPENID_PAYLOAD_USERNAME' in os.environ:
            config['PINGFEDERATE_OPENID_PAYLOAD_USERNAME'] = os.environ['PINGFEDERATE_OPENID_PAYLOAD_USERNAME'].split(
                ',')

        if 'PINGFEDERATE_OPENID_PAYLOAD_EMAIL' in os.environ:
            config['PINGFEDERATE_OPENID_PAYLOAD_EMAIL'] = os.environ['PINGFEDERATE_OPENID_PAYLOAD_EMAIL'].split(',')

        if 'PINGFEDERATE_OPENID_PAYLOAD_GROUP' in os.environ:
            config['PINGFEDERATE_OPENID_PAYLOAD_GROUP'] = os.environ['PINGFEDERATE_OPENID_PAYLOAD_GROUP'].split(',')

        if 'PINGFEDERATE_PUBKEY_LOCATION' in os.environ:
            config['PINGFEDERATE_PUBKEY_LOCATION'] = os.environ['PINGFEDERATE_PUBKEY_LOCATION'].split(',')

        if 'PINGFEDERATE_TOKEN_ALGORITHM' in os.environ:
            config['PINGFEDERATE_TOKEN_ALGORITHM'] = os.environ['PINGFEDERATE_TOKEN_ALGORITHM'].split(',')

        if 'CORS_ORIGINS' in os.environ:
            config['CORS_ORIGINS'] = os.environ['CORS_ORIGINS'].split(',')

        if 'MAIL_FROM' in os.environ:
            config['MAIL_FROM'] = os.environ['MAIL_FROM']

        if 'SMTP_PASSWORD' in os.environ:
            config['SMTP_PASSWORD'] = os.environ['SMTP_PASSWORD']

        if 'GOOGLE_TRACKING_ID' in os.environ:
            config['GOOGLE_TRACKING_ID'] = os.environ['GOOGLE_TRACKING_ID']

        if 'PLUGINS' in os.environ:
            config['PLUGINS'] = os.environ['PLUGINS'].split(',')

        # Runtime config check
        if config['CUSTOMER_VIEWS'] and not config['AUTH_REQUIRED']:
            raise RuntimeError('Must enable authentication to use customer views')

        if config['CUSTOMER_VIEWS'] and not config['ADMIN_USERS']:
            raise RuntimeError('Customer views is enabled but there are no admin users')

        return config

    @staticmethod
    def setup_logging(app: Flask) -> None:
        app.logger.removeHandler(default_handler)

        if app.config['LOG_FILE']:
            handler = RotatingFileHandler(
                filename=app.config['LOG_FILE'],
                maxBytes=app.config['LOG_MAX_BYTES'],
                backupCount=app.config['LOG_BACKUP_COUNT'],
                encoding='utf-8'
            )  # type: Handler
            app.logger.addHandler(handler)
        else:
            handler = logging.StreamHandler(wsgi_errors_stream)

        if app.debug:
            log_level = logging.DEBUG
        else:
            log_level = logging.INFO
        handler.setLevel(log_level)
        handler.setFormatter(logging.Formatter(app.config['LOG_FORMAT']))

        # for key in sorted(logging.Logger.manager.loggerDict):
        #     print('logging.getLogger(\'{}\'),'.format(key))

        loggers = [
            logging.getLogger('amqp'),
            logging.getLogger('asyncio'),
            logging.getLogger('celery'),
            logging.getLogger('concurrent'),
            logging.getLogger('flask'),
            logging.getLogger('kombu'),
            logging.getLogger('pymongo'),
            logging.getLogger('raven'),
            logging.getLogger('requests'),
            logging.getLogger('sentry'),
            logging.getLogger('urllib3'),
            logging.getLogger('werkzeug'),
        ]

        for logger in loggers:
            if not logger.handlers:
                logger.setLevel(log_level)
                logger.addHandler(handler)
