import os
import unittest

from alerta.utils.config import Config, Validate


class TestValidator(unittest.TestCase):
    '''
    Test the environment variables
    '''

    def setUp(self):
        self.TestValidator = Validate()

    def tearDown(self):
        pass

    def test_boolean_validator(self):
        self.assertEqual(self.TestValidator.validate_boolean('1'), True)
        self.assertEqual(self.TestValidator.validate_boolean('true'), True)
        self.assertEqual(self.TestValidator.validate_boolean('True'), True)
        self.assertEqual(self.TestValidator.validate_boolean('false'), False)
        self.assertEqual(self.TestValidator.validate_boolean('False'), False)
        self.assertEqual(self.TestValidator.validate_boolean('0'), False)

    def test_url_validator(self):
        self.assertEqual(self.TestValidator.validate_url('https://alerta.io'), 'https://alerta.io')
        self.assertEqual(self.TestValidator.validate_url('https://*.alerta.io'), 'https://*.alerta.io')
        self.assertEqual(self.TestValidator.validate_url('http://localhost.com'), 'http://localhost.com')

    def test_string_validator(self):
        self.assertEqual(self.TestValidator.validate_string('changeme'), 'changeme')
        self.assertEqual(self.TestValidator.validate_string(' '), ' ')
        self.assertEqual(self.TestValidator.validate_string('[changeme]'), '[changeme]')
        self.assertEqual(self.TestValidator.validate_string('jgfeujksegf7837546'), 'jgfeujksegf7837546')

    def test_email_validator(self):
        self.assertEqual(self.TestValidator.validate_email('name@namesen.com'), 'name@namesen.com')

    def test_integer_validator(self):
        self.assertEqual(self.TestValidator.validate_integer('2'), 2)

    def test_list_validator(self):
        self.assertEqual(self.TestValidator.validate_list('["admin"]', 'string'), ['admin'])
        self.assertEqual(self.TestValidator.validate_list('["admin", "admin@adminsen.com"]', 'string'), ['admin', 'admin@adminsen.com'])
        self.assertEqual(self.TestValidator.validate_list('admin', 'string'), ['admin'])
        self.assertEqual(self.TestValidator.validate_list('admin,name', 'string'), ['admin', 'name'])
        self.assertEqual(self.TestValidator.validate_list('["http://localhost.com"]', 'url'), ['http://localhost.com'])
        self.assertEqual(self.TestValidator.validate_list('["http://localhost.com", \'https://localhost.com\']', 'url'), ['http://localhost.com', 'https://localhost.com'])
        self.assertEqual(self.TestValidator.validate_list('["one", "two"]', 'string'), ['one', 'two'])
        self.assertEqual(self.TestValidator.validate_list('[1, 2]', 'integer'), [1, 2])
        self.assertEqual(self.TestValidator.validate_list('1,2', 'integer'), [1, 2])


class TestConfig(unittest.TestCase):
    '''
    Test the environment variables
    '''

    def setUp(self):
        self.TestConfig = Config()

    def tearDown(self):
        pass

    def test_get_user_config_debug(self):
        os.environ['DEBUG'] = '1'
        self.assertEqual(self.TestConfig.get_user_config()['DEBUG'], True)
        os.environ['DEBUG'] = 'True'
        self.assertEqual(self.TestConfig.get_user_config()['DEBUG'], True)
        os.environ['DEBUG'] = 'false'
        self.assertEqual(self.TestConfig.get_user_config()['DEBUG'], False)
        os.environ['DEBUG'] = '0'
        self.assertEqual(self.TestConfig.get_user_config()['DEBUG'], False)
        os.environ['DEBUG'] = 'off'
        self.assertEqual(self.TestConfig.get_user_config()['DEBUG'], False)

        del os.environ['DEBUG']

    def test_get_user_config_base_url(self):
        os.environ['BASE_URL'] = 'https://alerta.io'
        self.assertEqual(self.TestConfig.get_user_config()['BASE_URL'], os.environ['BASE_URL'])

        os.environ['BASE_URL'] = 'https://alerta.io'
        self.assertEqual(self.TestConfig.get_user_config()['BASE_URL'], 'https://alerta.io')
        os.environ['BASE_URL'] = 'https://*.alerta.io'
        self.assertEqual(self.TestConfig.get_user_config()['BASE_URL'], 'https://*.alerta.io')

        del os.environ['BASE_URL']

    def test_get_user_config_use_proxyfix(self):
        os.environ['USE_PROXYFIX'] = '1'
        self.assertEqual(self.TestConfig.get_user_config()['USE_PROXYFIX'], True)
        os.environ['USE_PROXYFIX'] = 'True'
        self.assertEqual(self.TestConfig.get_user_config()['USE_PROXYFIX'], True)
        os.environ['USE_PROXYFIX'] = 'false'
        self.assertEqual(self.TestConfig.get_user_config()['USE_PROXYFIX'], False)
        os.environ['USE_PROXYFIX'] = '0'
        self.assertEqual(self.TestConfig.get_user_config()['USE_PROXYFIX'], False)
        os.environ['USE_PROXYFIX'] = 'off'
        self.assertEqual(self.TestConfig.get_user_config()['USE_PROXYFIX'], False)

        del os.environ['USE_PROXYFIX']

    def test_get_user_config_secret_key(self):
        os.environ['SECRET_KEY'] = 'changeme'
        self.assertEqual(self.TestConfig.get_user_config()['SECRET_KEY'], os.environ['SECRET_KEY'])

        self.assertEqual(self.TestConfig.get_user_config()['SECRET_KEY'], 'changeme')
        os.environ['SECRET_KEY'] = 'jgfeujksegf7837546'
        self.assertEqual(self.TestConfig.get_user_config()['SECRET_KEY'], 'jgfeujksegf7837546')

        del os.environ['SECRET_KEY']

    def test_get_user_config_database_url(self):
        os.environ['DATABASE_URL'] = 'mongodb://localhost2:27017/monitoring'
        self.assertEqual(self.TestConfig.get_user_config()['DATABASE_URL'], 'mongodb://localhost2:27017/monitoring')

        del os.environ['DATABASE_URL']

    def test_get_user_config_database_name(self):
        os.environ['DATABASE_NAME'] = 'alerta'
        self.assertEqual(self.TestConfig.get_user_config()['DATABASE_NAME'], os.environ['DATABASE_NAME'])

        os.environ['DATABASE_NAME'] = ''
        self.assertEqual(self.TestConfig.get_user_config()['DATABASE_NAME'], '')
        os.environ['DATABASE_NAME'] = 'alerta'
        self.assertEqual(self.TestConfig.get_user_config()['DATABASE_NAME'], 'alerta')

        del os.environ['DATABASE_NAME']

    def test_get_user_config_auth_required(self):
        os.environ['AUTH_REQUIRED'] = '1'
        self.assertEqual(self.TestConfig.get_user_config()['AUTH_REQUIRED'], True)
        os.environ['AUTH_REQUIRED'] = 'True'
        self.assertEqual(self.TestConfig.get_user_config()['AUTH_REQUIRED'], True)
        os.environ['AUTH_REQUIRED'] = 'false'
        self.assertEqual(self.TestConfig.get_user_config()['AUTH_REQUIRED'], False)
        os.environ['AUTH_REQUIRED'] = '0'
        self.assertEqual(self.TestConfig.get_user_config()['AUTH_REQUIRED'], False)
        os.environ['AUTH_REQUIRED'] = 'off'
        self.assertEqual(self.TestConfig.get_user_config()['AUTH_REQUIRED'], False)

        del os.environ['AUTH_REQUIRED']

    def test_get_user_config_auth_provider(self):
        os.environ['AUTH_PROVIDER'] = 'basic'
        self.assertEqual(self.TestConfig.get_user_config()['AUTH_PROVIDER'], os.environ['AUTH_PROVIDER'])

        os.environ['AUTH_PROVIDER'] = 'basic'
        self.assertEqual(self.TestConfig.get_user_config()['AUTH_PROVIDER'], 'basic')
        os.environ['AUTH_PROVIDER'] = 'github'
        self.assertEqual(self.TestConfig.get_user_config()['AUTH_PROVIDER'], 'github')

        del os.environ['AUTH_PROVIDER']

    def test_get_user_config_admin_users(self):
        # Checking for backward compatibility
        os.environ['ADMIN_USERS'] = 'norman,name@namesen.com'
        self.assertEqual(self.TestConfig.get_user_config()['ADMIN_USERS'], ['norman', 'name@namesen.com'])

        # Testing new parsing
        os.environ['ADMIN_USERS'] = '["norman","name@namesen.com"]'
        self.assertEqual(self.TestConfig.get_user_config()['ADMIN_USERS'], ['norman', 'name@namesen.com'])

        del os.environ['ADMIN_USERS']

    def test_get_user_config_signup_enabled(self):
        os.environ['SIGNUP_ENABLED'] = '1'
        self.assertEqual(self.TestConfig.get_user_config()['SIGNUP_ENABLED'], True)
        os.environ['SIGNUP_ENABLED'] = 'True'
        self.assertEqual(self.TestConfig.get_user_config()['SIGNUP_ENABLED'], True)
        os.environ['SIGNUP_ENABLED'] = 'false'
        self.assertEqual(self.TestConfig.get_user_config()['SIGNUP_ENABLED'], False)
        os.environ['SIGNUP_ENABLED'] = '0'
        self.assertEqual(self.TestConfig.get_user_config()['SIGNUP_ENABLED'], False)
        os.environ['SIGNUP_ENABLED'] = 'off'
        self.assertEqual(self.TestConfig.get_user_config()['SIGNUP_ENABLED'], False)

        del os.environ['SIGNUP_ENABLED']

    def test_get_user_config_customer_views(self):
        os.environ['CUSTOMER_VIEWS'] = '1'
        os.environ['AUTH_REQUIRED'] = '1'
        os.environ['ADMIN_USERS'] = '["norman","name@namesen.com"]'
        self.assertEqual(self.TestConfig.get_user_config()['CUSTOMER_VIEWS'], True)
        os.environ['CUSTOMER_VIEWS'] = 'True'
        os.environ['AUTH_REQUIRED'] = '1'
        self.assertEqual(self.TestConfig.get_user_config()['CUSTOMER_VIEWS'], True)
        os.environ['CUSTOMER_VIEWS'] = 'false'
        self.assertEqual(self.TestConfig.get_user_config()['CUSTOMER_VIEWS'], False)
        os.environ['CUSTOMER_VIEWS'] = '0'
        self.assertEqual(self.TestConfig.get_user_config()['CUSTOMER_VIEWS'], False)
        os.environ['CUSTOMER_VIEWS'] = 'off'
        self.assertEqual(self.TestConfig.get_user_config()['CUSTOMER_VIEWS'], False)

        del os.environ['CUSTOMER_VIEWS']
        del os.environ['AUTH_REQUIRED']
        del os.environ['ADMIN_USERS']

    def test_get_user_config_oauth_client_id(self):
        os.environ['OAUTH2_CLIENT_ID'] = 'hhewkepwa78r57t4t65nk'
        self.assertEqual(self.TestConfig.get_user_config()['OAUTH2_CLIENT_ID'], os.environ['OAUTH2_CLIENT_ID'])

        os.environ['OAUTH2_CLIENT_ID'] = 'hhewkepwa78r57t4t65nk'
        self.assertEqual(self.TestConfig.get_user_config()['OAUTH2_CLIENT_ID'], 'hhewkepwa78r57t4t65nk')

        del os.environ['OAUTH2_CLIENT_ID']

    def test_get_user_config_oauth_client_secret(self):
        os.environ['OAUTH2_CLIENT_SECRET'] = 'secretkey'
        self.assertEqual(self.TestConfig.get_user_config()['OAUTH2_CLIENT_SECRET'], os.environ['OAUTH2_CLIENT_SECRET'])

        os.environ['OAUTH2_CLIENT_SECRET'] = 'secretkey'
        self.assertEqual(self.TestConfig.get_user_config()['OAUTH2_CLIENT_SECRET'], 'secretkey')

        del os.environ['OAUTH2_CLIENT_SECRET']

    def test_get_user_config_allowed_email_domains(self):
        # Checking for backward compatibility
        os.environ['ALLOWED_EMAIL_DOMAINS'] = '*'
        self.assertEqual(self.TestConfig.get_user_config()['ALLOWED_EMAIL_DOMAINS'], ['*'])
        os.environ['ALLOWED_EMAIL_DOMAINS'] = '*,gitlab.org'
        self.assertEqual(self.TestConfig.get_user_config()['ALLOWED_EMAIL_DOMAINS'], ['*', 'gitlab.org'])

        # Testing new parsing
        os.environ['ALLOWED_EMAIL_DOMAINS'] = '["*"]'
        self.assertEqual(self.TestConfig.get_user_config()['ALLOWED_EMAIL_DOMAINS'], ['*'])
        os.environ['ALLOWED_EMAIL_DOMAINS'] = '["github.com"]'
        self.assertEqual(self.TestConfig.get_user_config()['ALLOWED_EMAIL_DOMAINS'], ['github.com'])

        del os.environ['ALLOWED_EMAIL_DOMAINS']

    def test_get_user_config_azure_tenant(self):
        os.environ['AZURE_TENANT'] = 'common'
        self.assertEqual(self.TestConfig.get_user_config()['AZURE_TENANT'], os.environ['AZURE_TENANT'])

        os.environ['AZURE_TENANT'] = 'common'
        self.assertEqual(self.TestConfig.get_user_config()['AZURE_TENANT'], 'common')

        del os.environ['AZURE_TENANT']

    def test_get_user_config_github_url(self):
        os.environ['GITHUB_URL'] = 'https://github.com'
        self.assertEqual(self.TestConfig.get_user_config()['GITHUB_URL'], os.environ['GITHUB_URL'])

        os.environ['GITHUB_URL'] = 'https://github.com'
        self.assertEqual(self.TestConfig.get_user_config()['GITHUB_URL'], 'https://github.com')

        del os.environ['GITHUB_URL']

    def test_get_user_config_allowed_github_orgs(self):
        # Checking for backward compatibility
        os.environ['ALLOWED_GITHUB_ORGS'] = '*'
        self.assertEqual(self.TestConfig.get_user_config()['ALLOWED_GITHUB_ORGS'], ['*'])
        os.environ['ALLOWED_GITHUB_ORGS'] = '*,github.org'
        self.assertEqual(self.TestConfig.get_user_config()['ALLOWED_GITHUB_ORGS'], ['*', 'github.org'])

        # Testing new parsing
        os.environ['ALLOWED_GITHUB_ORGS'] = '["*","github.org"]'
        self.assertEqual(self.TestConfig.get_user_config()['ALLOWED_GITHUB_ORGS'], ['*', 'github.org'])

        del os.environ['ALLOWED_GITHUB_ORGS']

    def test_get_user_config_gitlab_url(self):
        os.environ['GITLAB_URL'] = 'https://gitlab.com'
        self.assertEqual(self.TestConfig.get_user_config()['GITLAB_URL'], os.environ['GITLAB_URL'])

        os.environ['GITLAB_URL'] = 'https://gitlab.com'
        self.assertEqual(self.TestConfig.get_user_config()['GITLAB_URL'], 'https://gitlab.com')

        del os.environ['GITLAB_URL']

    def test_get_user_config_allowed_gitlab_groups(self):
        # Checking for backward compatibility
        os.environ['ALLOWED_GITLAB_GROUPS'] = '*'
        self.assertEqual(self.TestConfig.get_user_config()['ALLOWED_OIDC_ROLES'], ['*'])
        os.environ['ALLOWED_GITLAB_GROUPS'] = '*,gitlab.org'
        self.assertEqual(self.TestConfig.get_user_config()['ALLOWED_OIDC_ROLES'], ['*', 'gitlab.org'])

        # Testing new parsing
        os.environ['ALLOWED_GITLAB_GROUPS'] = '["*","gitlab.org"]'
        self.assertEqual(self.TestConfig.get_user_config()['ALLOWED_OIDC_ROLES'], ['*', 'gitlab.org'])

        del os.environ['ALLOWED_GITLAB_GROUPS']

    def test_get_user_config_keycloak_url(self):
        os.environ['KEYCLOAK_URL'] = 'https://keycloak.com'
        self.assertEqual(self.TestConfig.get_user_config()['KEYCLOAK_URL'], os.environ['KEYCLOAK_URL'])

        os.environ['KEYCLOAK_URL'] = 'https://keycloak.com'
        self.assertEqual(self.TestConfig.get_user_config()['KEYCLOAK_URL'], 'https://keycloak.com')

        del os.environ['KEYCLOAK_URL']

    def test_get_user_config_keycloak_realm(self):
        os.environ['KEYCLOAK_REALM'] = 'realm'
        self.assertEqual(self.TestConfig.get_user_config()['KEYCLOAK_REALM'], os.environ['KEYCLOAK_REALM'])

        os.environ['KEYCLOAK_REALM'] = 'realm'
        self.assertEqual(self.TestConfig.get_user_config()['KEYCLOAK_REALM'], 'realm')

        del os.environ['KEYCLOAK_REALM']

    def test_get_user_config_allowed_keycloak_roles(self):
        # Checking for backward compatibility
        os.environ['ALLOWED_KEYCLOAK_ROLES'] = 'user'
        self.assertEqual(self.TestConfig.get_user_config()['ALLOWED_OIDC_ROLES'], ['user'])
        os.environ['ALLOWED_KEYCLOAK_ROLES'] = 'user,admin'
        self.assertEqual(self.TestConfig.get_user_config()['ALLOWED_OIDC_ROLES'], ['user', 'admin'])

        # Testing new parsing
        os.environ['ALLOWED_KEYCLOAK_ROLES'] = '["user","admin"]'
        self.assertEqual(self.TestConfig.get_user_config()['ALLOWED_OIDC_ROLES'], ['user', 'admin'])

        del os.environ['ALLOWED_KEYCLOAK_ROLES']

    def test_get_user_config_oidc_issuer_url(self):
        os.environ['OIDC_ISSUER_URL'] = 'https://oidc.com'
        self.assertEqual(self.TestConfig.get_user_config()['OIDC_ISSUER_URL'], os.environ['OIDC_ISSUER_URL'])

        os.environ['OIDC_ISSUER_URL'] = 'https://oidc.com'
        self.assertEqual(self.TestConfig.get_user_config()['OIDC_ISSUER_URL'], 'https://oidc.com')

        del os.environ['OIDC_ISSUER_URL']

    def test_get_user_config_allowed_oidc_roles(self):
        # Checking for backward compatibility
        os.environ['ALLOWED_OIDC_ROLES'] = 'user'
        self.assertEqual(self.TestConfig.get_user_config()['ALLOWED_OIDC_ROLES'], ['user'])
        os.environ['ALLOWED_OIDC_ROLES'] = 'user,admin'
        self.assertEqual(self.TestConfig.get_user_config()['ALLOWED_OIDC_ROLES'], ['user', 'admin'])

        # Testing new parsing
        os.environ['ALLOWED_OIDC_ROLES'] = '["user","admin"]'
        self.assertEqual(self.TestConfig.get_user_config()['ALLOWED_OIDC_ROLES'], ['user', 'admin'])

        del os.environ['ALLOWED_OIDC_ROLES']

    def test_get_user_config_cors_origins(self):
        # Checking for backward compatibility
        os.environ['CORS_ORIGINS'] = 'http://localhost'
        self.assertEqual(self.TestConfig.get_user_config()['CORS_ORIGINS'], ['http://localhost'])
        os.environ['CORS_ORIGINS'] = 'http://localhost,http://localhost:8000,https://*.local.alerta.io:8080'
        self.assertEqual(self.TestConfig.get_user_config()['CORS_ORIGINS'], ['http://localhost', 'http://localhost:8000', 'https://*.local.alerta.io:8080'])

        # Testing new parsing
        os.environ['CORS_ORIGINS'] = '["http://localhost","http://localhost:8000","https://*.local.alerta.io:8080"]'
        self.assertEqual(self.TestConfig.get_user_config()['CORS_ORIGINS'], ['http://localhost', 'http://localhost:8000', 'https://*.local.alerta.io:8080'])

        del os.environ['CORS_ORIGINS']

    def test_get_user_config_mail_from(self):
        os.environ['MAIL_FROM'] = 'name@namesen.com'
        self.assertEqual(self.TestConfig.get_user_config()['MAIL_FROM'], os.environ['MAIL_FROM'])

        os.environ['MAIL_FROM'] = 'name@namesen.com'
        self.assertEqual(self.TestConfig.get_user_config()['MAIL_FROM'], 'name@namesen.com')

        del os.environ['MAIL_FROM']

    def test_get_user_config_smtp_password(self):
        os.environ['SMTP_PASSWORD'] = 'smtppassword'
        self.assertEqual(self.TestConfig.get_user_config()['SMTP_PASSWORD'], os.environ['SMTP_PASSWORD'])

        os.environ['SMTP_PASSWORD'] = 'smtppassword'
        self.assertEqual(self.TestConfig.get_user_config()['SMTP_PASSWORD'], 'smtppassword')

        del os.environ['SMTP_PASSWORD']

    def test_get_user_config_google_tracking_id(self):
        os.environ['GOOGLE_TRACKING_ID'] = 'fdkngfjunfnjf984375'
        self.assertEqual(self.TestConfig.get_user_config()['GOOGLE_TRACKING_ID'], os.environ['GOOGLE_TRACKING_ID'])

        os.environ['GOOGLE_TRACKING_ID'] = 'fdkngfjunfnjf984375'
        self.assertEqual(self.TestConfig.get_user_config()['GOOGLE_TRACKING_ID'], 'fdkngfjunfnjf984375')

        del os.environ['GOOGLE_TRACKING_ID']

    def test_get_user_config_plugins(self):
        # Checking for backward compatibility
        os.environ['PLUGINS'] = 'remote_ip'
        self.assertEqual(self.TestConfig.get_user_config()['PLUGINS'], ['remote_ip'])
        os.environ['PLUGINS'] = 'remote_ip,reject'
        self.assertEqual(self.TestConfig.get_user_config()['PLUGINS'], ['remote_ip', 'reject'])

        # Testing new parsing
        os.environ['PLUGINS'] = '["remote_ip","reject"]'
        self.assertEqual(self.TestConfig.get_user_config()['PLUGINS'], ['remote_ip', 'reject'])

        del os.environ['PLUGINS']

    def test_get_user_config_alert_timeout(self):
        os.environ['ALERT_TIMEOUT'] = '300'
        self.assertEqual(self.TestConfig.get_user_config()['ALERT_TIMEOUT'], 300)

        del os.environ['ALERT_TIMEOUT']

    def test_get_user_config_heartbeat_timeout(self):
        os.environ['HEARTBEAT_TIMEOUT'] = '300'
        self.assertEqual(self.TestConfig.get_user_config()['HEARTBEAT_TIMEOUT'], 300)

        del os.environ['HEARTBEAT_TIMEOUT']

    def test_get_user_config_api_key_expire_days(self):
        os.environ['API_KEY_EXPIRE_DAYS'] = '365'
        self.assertEqual(self.TestConfig.get_user_config()['API_KEY_EXPIRE_DAYS'], 365)

        del os.environ['API_KEY_EXPIRE_DAYS']
