import os
import unittest
from alerta.utils.config import Config, Validator


class TestValidator(unittest.TestCase):
    """
    Test the environment variables
    """
    def setUp(self):
        self.TestValidator = Validator()
        self.TestConfig = Config()

    def test_boolean_validator(self):
        self.assertEqual(self.TestValidator.boolean_validator('1'), True)
        self.assertEqual(self.TestValidator.boolean_validator('true'), True)
        self.assertEqual(self.TestValidator.boolean_validator('True'), True)
        self.assertEqual(self.TestValidator.boolean_validator('false'), False)
        self.assertEqual(self.TestValidator.boolean_validator('False'), False)
        self.assertEqual(self.TestValidator.boolean_validator('0'), False)
        self.assertEqual(self.TestValidator.boolean_validator(0), None)
        self.assertEqual(self.TestValidator.boolean_validator("[0]"), None)

    def test_get_user_config_debug(self):
        os.environ["DEBUG"] = "1"
        self.assertEqual(self.TestConfig.get_user_config()['DEBUG'], True)
        os.environ["DEBUG"] = "True"
        self.assertEqual(self.TestConfig.get_user_config()['DEBUG'], True)
        os.environ["DEBUG"] = "false"
        self.assertEqual(self.TestConfig.get_user_config()['DEBUG'], False)
        os.environ["DEBUG"] = "0"
        self.assertEqual(self.TestConfig.get_user_config()['DEBUG'], False)
        os.environ["DEBUG"] = "off"
        self.assertEqual(self.TestConfig.get_user_config()['DEBUG'], None)

    def test_get_user_config_base_url(self):
        os.environ["BASE_URL"] = "https://alerta.io"
        self.assertEqual(self.TestConfig.get_user_config()['BASE_URL'], 'https://alerta.io')
        os.environ["BASE_URL"] = "https://*.alerta.io"
        self.assertEqual(self.TestConfig.get_user_config()['BASE_URL'], 'https://*.alerta.io')
        os.environ["BASE_URL"] = ""
        self.assertEqual(self.TestConfig.get_user_config()['BASE_URL'], '')
        os.environ["BASE_URL"] = "none"
        self.assertEqual(self.TestConfig.get_user_config()['BASE_URL'], '')

    def test_get_user_config_use_proxyfix(self):
        os.environ["USE_PROXYFIX"] = "1"
        self.assertEqual(self.TestConfig.get_user_config()['USE_PROXYFIX'], True)
        os.environ["USE_PROXYFIX"] = "True"
        self.assertEqual(self.TestConfig.get_user_config()['USE_PROXYFIX'], True)
        os.environ["USE_PROXYFIX"] = "false"
        self.assertEqual(self.TestConfig.get_user_config()['USE_PROXYFIX'], False)
        os.environ["USE_PROXYFIX"] = "0"
        self.assertEqual(self.TestConfig.get_user_config()['USE_PROXYFIX'], False)
        os.environ["USE_PROXYFIX"] = "off"
        self.assertEqual(self.TestConfig.get_user_config()['USE_PROXYFIX'], None)

    def test_get_user_config_secret_key(self):
        self.assertEqual(self.TestConfig.get_user_config()['SECRET_KEY'], 'changeme')
        os.environ["SECRET_KEY"] = "jgfeujksegf7837546"
        self.assertEqual(self.TestConfig.get_user_config()['SECRET_KEY'], 'jgfeujksegf7837546')

    def test_get_user_config_database_url(self):
        os.environ["DATABASE_URL"] = "mongodb://db:27017/monitoring"
        self.assertEqual(self.TestConfig.get_user_config()['DATABASE_URL'], 'mongodb://db:27017/monitoring')

    def test_get_user_config_database_name(self):
        os.environ["DATABASE_NAME"] = ""
        self.assertEqual(self.TestConfig.get_user_config()['DATABASE_NAME'], '')
        os.environ["DATABASE_NAME"] = "alerta"
        self.assertEqual(self.TestConfig.get_user_config()['DATABASE_NAME'], 'alerta')

    def test_get_user_config_auth_required(self):
        os.environ["AUTH_REQUIRED"] = "1"
        self.assertEqual(self.TestConfig.get_user_config()['AUTH_REQUIRED'], True)
        os.environ["AUTH_REQUIRED"] = "True"
        self.assertEqual(self.TestConfig.get_user_config()['AUTH_REQUIRED'], True)
        os.environ["AUTH_REQUIRED"] = "false"
        self.assertEqual(self.TestConfig.get_user_config()['AUTH_REQUIRED'], False)
        os.environ["AUTH_REQUIRED"] = "0"
        self.assertEqual(self.TestConfig.get_user_config()['AUTH_REQUIRED'], False)
        os.environ["AUTH_REQUIRED"] = "off"
        self.assertEqual(self.TestConfig.get_user_config()['AUTH_REQUIRED'], None)

    def test_get_user_config_auth_provider(self):
        os.environ["AUTH_PROVIDER"] = "basic"
        self.assertEqual(self.TestConfig.get_user_config()['AUTH_PROVIDER'], "basic")
        os.environ["AUTH_PROVIDER"] = "github"
        self.assertEqual(self.TestConfig.get_user_config()['AUTH_PROVIDER'], "github")

    def test_get_user_config_admin_users(self):
        os.environ["ADMIN_USERS"] = "['norman','name@namesen.com']"
        self.assertEqual(self.TestConfig.get_user_config()['ADMIN_USERS'], ['norman','name@namesen.com'])

    def test_get_user_config_signup_enabled(self):
        os.environ["SIGNUP_ENABLED"] = "1"
        self.assertEqual(self.TestConfig.get_user_config()['SIGNUP_ENABLED'], True)
        os.environ["SIGNUP_ENABLED"] = "True"
        self.assertEqual(self.TestConfig.get_user_config()['SIGNUP_ENABLED'], True)
        os.environ["SIGNUP_ENABLED"] = "false"
        self.assertEqual(self.TestConfig.get_user_config()['SIGNUP_ENABLED'], False)
        os.environ["SIGNUP_ENABLED"] = "0"
        self.assertEqual(self.TestConfig.get_user_config()['SIGNUP_ENABLED'], False)
        os.environ["SIGNUP_ENABLED"] = "off"
        self.assertEqual(self.TestConfig.get_user_config()['SIGNUP_ENABLED'], None)

    def test_get_user_config_customer_views(self):
        os.environ["CUSTOMER_VIEWS"] = "1"
        os.environ["AUTH_REQUIRED"] = "1"
        self.assertEqual(self.TestConfig.get_user_config()['CUSTOMER_VIEWS'], True)
        os.environ["CUSTOMER_VIEWS"] = "True"
        os.environ["AUTH_REQUIRED"] = "1"
        self.assertEqual(self.TestConfig.get_user_config()['CUSTOMER_VIEWS'], True)
        os.environ["CUSTOMER_VIEWS"] = "false"
        self.assertEqual(self.TestConfig.get_user_config()['CUSTOMER_VIEWS'], False)
        os.environ["CUSTOMER_VIEWS"] = "0"
        self.assertEqual(self.TestConfig.get_user_config()['CUSTOMER_VIEWS'], False)
        os.environ["CUSTOMER_VIEWS"] = "off"
        self.assertEqual(self.TestConfig.get_user_config()['CUSTOMER_VIEWS'], None)

    def test_get_user_config_oauth_client_id(self):
        os.environ["OAUTH2_CLIENT_ID"] = "hhewkepwa78r57t4t65nk"
        self.assertEqual(self.TestConfig.get_user_config()['OAUTH2_CLIENT_ID'], 'hhewkepwa78r57t4t65nk')

    def test_get_user_config_oauth_client_secret(self):
        os.environ["OAUTH2_CLIENT_SECRET"] = "secretkey"
        self.assertEqual(self.TestConfig.get_user_config()['OAUTH2_CLIENT_SECRET'], 'secretkey')

    def test_get_user_config_allowed_email_domains(self):
        os.environ["ALLOWED_EMAIL_DOMAINS"] = "['*']"
        self.assertEqual(self.TestConfig.get_user_config()['ALLOWED_EMAIL_DOMAINS'], ['*'])
        os.environ["ALLOWED_EMAIL_DOMAINS"] = "['github.com']"
        self.assertEqual(self.TestConfig.get_user_config()['ALLOWED_EMAIL_DOMAINS'], ['github.com'])

    def test_get_user_config_azure_tenant(self):
        os.environ["AZURE_TENANT"] = "common"
        self.assertEqual(self.TestConfig.get_user_config()['AZURE_TENANT'], 'common')

    def test_get_user_config_github_url(self):
        os.environ["GITHUB_URL"] = "https://github.com"
        self.assertEqual(self.TestConfig.get_user_config()['GITHUB_URL'], 'https://github.com')

    def test_get_user_config_allowed_github_orgs(self):
        os.environ["ALLOWED_GITHUB_ORGS"] = "['*','github.org']"
        self.assertEqual(self.TestConfig.get_user_config()['ALLOWED_GITHUB_ORGS'], ['*', 'github.org'])

    def test_get_user_config_gitlab_url(self):
        os.environ["GITLAB_URL"] = "https://gitlab.com"
        self.assertEqual(self.TestConfig.get_user_config()['GITLAB_URL'], 'https://gitlab.com')

    def test_get_user_config_allowed_gitlab_groups(self):
        os.environ["ALLOWED_GITLAB_GROUPS"] = "['*','gitlab.org']"
        self.assertEqual(self.TestConfig.get_user_config()['ALLOWED_GITLAB_GROUPS'], ['*', 'gitlab.org'])

    def test_get_user_config_keycloak_url(self):
        os.environ["KEYCLOAK_URL"] = "https://keycloak.com"
        self.assertEqual(self.TestConfig.get_user_config()['KEYCLOAK_URL'], 'https://keycloak.com')

    def test_get_user_config_keycloak_realm(self):
        os.environ["KEYCLOAK_REALM"] = "realm"
        self.assertEqual(self.TestConfig.get_user_config()['KEYCLOAK_REALM'], 'realm')

    def test_get_user_config_allowed_keycloak_roles(self):
        os.environ["ALLOWED_KEYCLOAK_ROLES"] = "['user','admin']"
        self.assertEqual(self.TestConfig.get_user_config()['ALLOWED_KEYCLOAK_ROLES'], ['user', 'admin'])

    def test_get_user_config_oidc_issuer_url(self):
        os.environ["OIDC_ISSUER_URL"] = "https://oidc.com"
        self.assertEqual(self.TestConfig.get_user_config()['OIDC_ISSUER_URL'], 'https://oidc.com')

    def test_get_user_config_allowed_oidc_roles(self):
        os.environ["ALLOWED_OIDC_ROLES"] = "['user','admin']"
        self.assertEqual(self.TestConfig.get_user_config()['ALLOWED_OIDC_ROLES'], ['user', 'admin'])

    def test_get_user_config_cors_origins(self):
        os.environ["CORS_ORIGINS"] = "['http://localhost','http://localhost:8000','https://*.local.alerta.io:8080']"
        self.assertEqual(self.TestConfig.get_user_config()['CORS_ORIGINS'], ['http://localhost', 'http://localhost:8000', 'https://*.local.alerta.io:8080'])

    def test_get_user_config_mail_from(self):
        os.environ["MAIL_FROM"] = "name@namesen.com"
        self.assertEqual(self.TestConfig.get_user_config()['MAIL_FROM'], 'name@namesen.com')

    def test_get_user_config_smtp_password(self):
        os.environ["SMTP_PASSWORD"] = "smtppassword"
        self.assertEqual(self.TestConfig.get_user_config()['SMTP_PASSWORD'], 'smtppassword')

    def test_get_user_config_google_tracking_id(self):
        os.environ["GOOGLE_TRACKING_ID"] = "fdkngfjunfnjf984375"
        self.assertEqual(self.TestConfig.get_user_config()['GOOGLE_TRACKING_ID'], 'fdkngfjunfnjf984375')

    def test_get_user_config_plugins(self):
        os.environ["PLUGINS"] = "['remote_ip','reject']"
        self.assertEqual(self.TestConfig.get_user_config()['PLUGINS'], ['remote_ip', 'reject'])

    def test_get_user_config_alert_timeout(self):
        os.environ["ALERT_TIMEOUT"] = "300"
        self.assertEqual(self.TestConfig.get_user_config()['ALERT_TIMEOUT'], 300)

    def test_get_user_config_heartbeat_timeout(self):
        os.environ["HEARTBEAT_TIMEOUT"] = "300"
        self.assertEqual(self.TestConfig.get_user_config()['HEARTBEAT_TIMEOUT'], 300)

    def test_get_user_config_api_key_expire_days(self):
        os.environ["API_KEY_EXPIRE_DAYS"] = "365"
        self.assertEqual(self.TestConfig.get_user_config()['API_KEY_EXPIRE_DAYS'], 365)
