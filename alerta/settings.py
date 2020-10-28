#
# ***** ALERTA SERVER DEFAULT SETTINGS -- DO NOT MODIFY THIS FILE *****
#
# To override these settings use /etc/alertad.conf or the contents of the
# configuration file set by the environment variable ALERTA_SVR_CONF_FILE.
#
# Further information on settings can be found at https://docs.alerta.io

from typing import Any, Dict, List, Tuple  # noqa

DEBUG = False

BASE_URL = ''
USE_PROXYFIX = False
SECRET_KEY = 'changeme'

# Logging configuration
LOG_CONFIG_FILE = ''
LOG_HANDLERS = ['console']  # ['console', 'file', 'wsgi']
LOG_FILE = 'alertad.log'  # NOTE: 'file' must be added to LOG_HANDLERS for logging to work
LOG_LEVEL = 'WARNING'  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 2
LOG_FORMAT = 'default'  # 'default', 'simple', 'verbose', 'json' or any valid logging format
LOG_METHODS = ['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'CONNECT', 'OPTIONS', 'TRACE', 'PATCH']

# API settings
ALARM_MODEL = 'ALERTA'  # 'ALERTA' (default) or 'ISA_18_2'
QUERY_LIMIT = 50
DEFAULT_PAGE_SIZE = QUERY_LIMIT  # maximum number of alerts returned by a single query
HISTORY_LIMIT = 100  # cap the number of alert history entries
HISTORY_ON_VALUE_CHANGE = True  # history entry for duplicate alerts if value changes

# MongoDB (deprecated, use DATABASE_URL setting)
MONGO_URI = 'mongodb://localhost:27017/monitoring'
MONGO_DATABASE = None  # can be used to override default database, above
MONGO_RAISE_ON_ERROR = True

# PostgreSQL (deprecated, use DATABASE_URL setting)
POSTGRES_URI = 'postgres://localhost:5432/monitoring'  # not used (use DATABASE_URL)
POSTGRES_DB = None

# Database
DATABASE_URL = MONGO_URI  # default: MongoDB
DATABASE_NAME = MONGO_DATABASE or POSTGRES_DB
DATABASE_RAISE_ON_ERROR = MONGO_RAISE_ON_ERROR  # True - terminate, False - ignore and continue

# Search
DEFAULT_FIELD = 'text'  # default field if no search prefix specified (Postgres only)

# Bulk API
BULK_QUERY_LIMIT = 100000  # max number of alerts for bulk endpoints
CELERY_BROKER_URL = None
CELERY_RESULT_BACKEND = None
CELERY_ACCEPT_CONTENT = ['customjson']
CELERY_TASK_SERIALIZER = 'customjson'
CELERY_RESULT_SERIALIZER = 'customjson'

# Authentication settings
AUTH_REQUIRED = False
AUTH_PROVIDER = 'basic'  # basic (default), ldap, github, openid, saml2, azure, cognito, gitlab, google, keycloak
ADMIN_USERS = []  # type: List[str]
DEFAULT_ADMIN_ROLE = 'admin'
ADMIN_ROLES = [DEFAULT_ADMIN_ROLE]
DEFAULT_USER_ROLE = 'user'
USER_ROLES = [DEFAULT_USER_ROLE]
USER_DEFAULT_SCOPES = ['read', 'write']  # Note: 'write' scope implicitly includes 'read'
DEFAULT_GUEST_ROLE = 'guest'
GUEST_ROLES = [DEFAULT_GUEST_ROLE]
GUEST_DEFAULT_SCOPES = ['read:alerts']
CUSTOMER_VIEWS = False

BASIC_AUTH_REALM = 'Alerta'
SIGNUP_ENABLED = True

HMAC_AUTH_CREDENTIALS = [
    # {
    #     'id': '',  # access key id  => $ uuidgen | tr '[:upper:]' '[:lower:]'
    #     'key': '',  # secret key => $ date | md5 | base64
    #     'algorithm': 'sha256'  # valid hmac algorithm eg. sha256, sha384, sha512
    # }
]  # type: List[Dict[str, Any]]

OAUTH2_CLIENT_ID = None  # OAuth2 client ID and secret
OAUTH2_CLIENT_SECRET = None
ALLOWED_EMAIL_DOMAINS = ['*']

# Amazon Cognito
AWS_REGION = 'us-east-1'  # US East - N. Virginia (default)
COGNITO_USER_POOL_ID = None
COGNITO_DOMAIN = None

# GitHub OAuth2
GITHUB_URL = 'https://github.com'
ALLOWED_GITHUB_ORGS = ['*']

# GitLab OAuth2
GITLAB_URL = 'https://gitlab.com'
ALLOWED_GITLAB_GROUPS = None

# BasicAuth using LDAP
LDAP_URL = ''  # eg. ldap://localhost:389
LDAP_BASEDN = ''
LDAP_CACERT = ''  # Path to CA certificate to verify LDAPS connection against
LDAP_ALLOW_SELF_SIGNED_CERT = False
LDAP_DOMAINS = {
    # 'planetexpress.com': 'cn=%s,ou=people,dc=planetexpress,dc=com'
}
LDAP_BIND_USERNAME = ''  # required if using LDAP_SEARCH_QUERY eg. uid=admin,ou=users,dc=domain,dc=com
LDAP_BIND_PASSWORD = ''  # required if using LDAP_BIND_USERNAME
LDAP_USER_BASEDN = ''  # BASEDN for user search (default: LDAP_BASEDN)
LDAP_USER_FILTER = ''  # eg. (cn={username})
LDAP_USER_NAME_ATTR = 'cn'  # eg. cn or displayName
LDAP_USER_EMAIL_ATTR = 'mail'  # eg. mail or email
LDAP_GROUP_BASEDN = ''  # BASEDN for group search (default: LDAP_BASEDN)
LDAP_GROUP_FILTER = ''  # eg. (&(member={userdn})(objectClass=group))
LDAP_GROUP_NAME_ATTR = 'memberOf'  # eg. memberOf or cn
LDAP_DEFAULT_DOMAIN = ''  # if set allows users to login with bare username

# Microsoft Identity Platform (v2.0)
AZURE_TENANT = 'common'  # "common", "organizations", "consumers" or tenant ID

# Keycloak
KEYCLOAK_URL = None
KEYCLOAK_REALM = None
ALLOWED_KEYCLOAK_ROLES = None

# OpenID Connect
OIDC_ISSUER_URL = None
OIDC_AUTH_URL = None
OIDC_LOGOUT_URL = None
OIDC_VERIFY_TOKEN = False
OIDC_ROLE_CLAIM = OIDC_CUSTOM_CLAIM = 'roles'  # JWT claim name whose value is used in role mapping
OIDC_GROUP_CLAIM = 'groups'  # JWT claim name whose value is used in customer mapping
ALLOWED_OIDC_ROLES = ALLOWED_GITLAB_GROUPS or ALLOWED_KEYCLOAK_ROLES or ['*']

# SAML 2.0
SAML2_ENTITY_ID = None
SAML2_METADATA_URL = None
SAML2_USER_NAME_FORMAT = '{givenName} {surname}'
SAML2_EMAIL_ATTRIBUTE = 'emailAddress'
SAML2_CONFIG = {}  # type: Dict[str, Any]
ALLOWED_SAML2_GROUPS = ['*']

TOKEN_EXPIRE_DAYS = 14
API_KEY_EXPIRE_DAYS = 365  # 1 year

# Audit Log
AUDIT_TRAIL = ['admin']  # possible categories are 'admin', 'write', and 'auth'
AUDIT_LOG = None  # set to True to log to application logger
AUDIT_LOG_REDACT = True  # redact sensitive data before logging
AUDIT_LOG_JSON = False  # log alert data as JSON object
AUDIT_URL = None  # send audit log events via webhook URL

# CORS settings
CORS_ALLOW_HEADERS = ['Content-Type', 'Authorization', 'Access-Control-Allow-Origin']
CORS_ORIGINS = [
    # 'http://try.alerta.io',
    # 'http://explorer.alerta.io',
    'http://localhost',
    'http://localhost:8000',
    r'https?://\w*\.?local\.alerta\.io:?\d*/?.*'  # => http(s)://*.local.alerta.io:<port>
]
CORS_SUPPORTS_CREDENTIALS = AUTH_REQUIRED

# Serverity settings
SEVERITY_MAP = {}  # type: Dict[str, Any]
DEFAULT_NORMAL_SEVERITY = None
DEFAULT_PREVIOUS_SEVERITY = None
COLOR_MAP = {}  # type: Dict[str, Any]

# Timeout settings
DEFAULT_TIMEOUT = 86400  # seconds
ALERT_TIMEOUT = DEFAULT_TIMEOUT
HEARTBEAT_TIMEOUT = DEFAULT_TIMEOUT
HEARTBEAT_MAX_LATENCY = 2000  # ms
ACK_TIMEOUT = 0  # auto-unack alerts after x seconds (0 seconds = do not auto-unack)
SHELVE_TIMEOUT = 7200  # auto-unshelve alerts after x seconds (0 seconds = do not auto-unshelve)

# Housekeeping settings
DEFAULT_EXPIRED_DELETE_HRS = 2  # hours (0 hours = do not delete)
DEFAULT_INFO_DELETE_HRS = 12  # hours (0 hours = do not delete)

# Send verification emails to new BasicAuth users
EMAIL_VERIFICATION = False
SMTP_HOST = 'smtp.gmail.com'
SMTP_PORT = 587
MAIL_LOCALHOST = 'localhost'  # mail server to use in HELO/EHLO command
SMTP_STARTTLS = True
SMTP_USE_SSL = False
SSL_KEY_FILE = None
SSL_CERT_FILE = None
MAIL_FROM = ''  # replace with valid sender address eg you@gmail.com
SMTP_USERNAME = ''  # application-specific username if different to MAIL_FROM user
SMTP_PASSWORD = ''  # password for MAIL_FROM (or SMTP_USERNAME if used)

# Web console settings
SITE_LOGO_URL = ''  # URL to company logo
DATE_FORMAT_LONG_DATE = 'ddd D MMM, YYYY HH:mm:ss.SSS Z'  # eg. Tue 9 Oct, 2018 09:24.036 +02:00
DATE_FORMAT_MEDIUM_DATE = 'ddd D MMM HH:mm'  # eg. Tue 9 Oct 09:24
DATE_FORMAT_SHORT_TIME = 'HH:mm'  # eg. 09:24
DEFAULT_AUDIO_FILE = None  # must exist on client at relative path eg. '/audio/alert_high-intensity.ogg' or URL
COLUMNS = [
    'severity', 'status', 'lastReceiveTime', 'timeoutLeft', 'duplicateCount',
    'customer', 'environment', 'service', 'resource', 'event', 'value', 'text'
]
SORT_LIST_BY = ['severity', 'lastReceiveTime']  # eg. newest='lastReceiveTime' or oldest='-createTime' (Note: minus means reverse)
DEFAULT_FILTER = {'status': ['open', 'ack']}

# Alert Status Indicators
ASI_SEVERITY = [
    'critical', 'major', 'minor', 'warning', 'indeterminate', 'informational'
]
ASI_QUERIES = [
    {'text': 'Production', 'query': [['environment', 'Production']]},
    {'text': 'Development', 'query': [['environment', 'Development']]},
    {'text': 'Heartbeats', 'query': {'q': 'event:Heartbeat'}},
    {'text': 'Misc.', 'query': 'group=Misc'},
]

# Alarm list default font settings
DEFAULT_FONT = {
    'font-family': '"Sintony", Arial, sans-serif',
    'font-size': '13px',
    'font-weight': 500  # 400=normal, 700=bold
}

# List of custom actions
ACTIONS = []  # type: List[str]
GOOGLE_TRACKING_ID = None
AUTO_REFRESH_INTERVAL = 5000  # ms

# Plugins
PLUGINS = ['remote_ip', 'reject', 'heartbeat', 'blackout', 'forwarder']
PLUGINS_RAISE_ON_ERROR = True  # raise RuntimeError exception on first failure

# reject plugin settings
ORIGIN_BLACKLIST = []  # type: List[str]
# ORIGIN_BLACKLIST = ['foo/bar$', '.*/qux']  # reject all foo alerts from bar, and everything from qux
ALLOWED_ENVIRONMENTS = ['Production', 'Development']  # reject alerts without allowed environments

# blackout settings
BLACKOUT_DURATION = 3600  # default period = 1 hour
NOTIFICATION_BLACKOUT = False  # True - set alert status=blackout, False - do not process alert (default)
BLACKOUT_ACCEPT = []  # type: List[str]
# BLACKOUT_ACCEPT = ['normal', 'ok', 'cleared']  # list of severities accepted during blackout period

# northbound interface
FWD_DESTINATIONS = [
    # ('http://localhost:9000', {'username': 'user', 'password': 'pa55w0rd', 'timeout': 10}, ['alerts', 'actions']),  # BasicAuth
    # ('https://httpbin.org/anything', dict(username='foo', password='bar', ssl_verify=False), ['alerts', 'actions']),
    # ('http://localhost:9000', {'key': 'access-key', 'secret': 'secret-key'}, ['alerts', 'actions']),  # Hawk HMAC
    # ('http://localhost:9000', {'key': 'my-api-key'}, ['alerts', 'actions']),  # API key
    # ('http://localhost:9000', {'token': 'bearer-token'}, ['alerts', 'actions']),  # Bearer token
]  # type: List[Tuple]

# valid actions=['*', 'alerts', 'actions', 'open', 'assign', 'ack', 'unack', 'shelve', 'unshelve', 'close', 'delete']
