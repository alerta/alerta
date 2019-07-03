#
# ***** ALERTA SERVER DEFAULT SETTINGS -- DO NOT MODIFY THIS FILE *****
#
# To override these settings use /etc/alertad.conf or the contents of the
# configuration file set by the environment variable ALERTA_SVR_CONF_FILE.
#
# Further information on settings can be found at https://docs.alerta.io

from typing import Any, Dict, List  # noqa

DEBUG = False

BASE_URL = ''
USE_PROXYFIX = False
SECRET_KEY = 'changeme'

# Logging configuration
LOG_CONFIG_FILE = ''
LOG_HANDLERS = ['console']  # ['console', 'file', 'wsgi']
LOG_FILE = 'alertad.log'  # NOTE: 'file' must be added to LOG_HANDLERS for logging to work
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 2
LOG_FORMAT = 'default'  # ['default', 'simple', 'verbose', 'json'] or any valid logging format
LOG_METHODS = ['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'CONNECT', 'OPTIONS', 'TRACE', 'PATCH']

# API settings
ALARM_MODEL = 'ALERTA'  # 'ALERTA' (default) or 'ISA_18_2'
QUERY_LIMIT = 1000
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
USER_DEFAULT_SCOPES = ['read', 'write']  # Note: 'write' scope implicitly includes 'read'
CUSTOMER_VIEWS = False

BASIC_AUTH_REALM = 'Alerta'
SIGNUP_ENABLED = True

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
LDAP_DOMAINS = {}  # type: Dict[str, str]
LDAP_DOMAINS_GROUP = {}  # type: Dict[str, str]
LDAP_DOMAINS_BASEDN = {}  # type: Dict[str, str]

# Microsoft Identity Platform (v2.0)
AZURE_TENANT = 'common'  # "common", "organizations", "consumers" or tenant ID

# Keycloak
KEYCLOAK_URL = None
KEYCLOAK_REALM = None
ALLOWED_KEYCLOAK_ROLES = None

# OpenID Connect
OIDC_ISSUER_URL = None
OIDC_AUTH_URL = None
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
DEFAULT_TIMEOUT = 86400
ALERT_TIMEOUT = DEFAULT_TIMEOUT
HEARTBEAT_TIMEOUT = DEFAULT_TIMEOUT

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
DATE_FORMAT_SHORT_TIME = 'HH:mm'  # eg. 09:24
DATE_FORMAT_MEDIUM_DATE = 'EEE d MMM HH:mm'  # eg. Tue 9 Oct 09:24
DATE_FORMAT_LONG_DATE = 'd/M/yyyy h:mm:ss.sss a'  # eg. 9/10/2018 9:24:03.036 AM
DEFAULT_AUDIO_FILE = None  # must exist on client at relative path eg. '/audio/alert_high-intensity.ogg' or URL
COLUMNS = [
    'severity', 'status', 'lastReceiveTime', 'timeoutLeft', 'duplicateCount',
    'customer', 'environment', 'service', 'resource', 'event', 'value'
]
SORT_LIST_BY = 'lastReceiveTime'  # newest='lastReceiveTime' or oldest='-createTime' (Note: minus means reverse)

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

# List of custom actions
ACTIONS = []  # type: List[str]
GOOGLE_TRACKING_ID = None
AUTO_REFRESH_INTERVAL = 5000  # ms

# Plugins
PLUGINS = ['remote_ip', 'reject', 'heartbeat', 'blackout']
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
