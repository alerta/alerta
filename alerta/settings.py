#
# ***** ALERTA SERVER DEFAULT SETTINGS -- DO NOT MODIFY THIS FILE *****
#
# To override these settings use /etc/alertad.conf or the contents of the
# configuration file set by the environment variable ALERTA_SVR_CONF_FILE.
#
# Further information on settings can be found at http://docs.alerta.io

from typing import Dict, List  # noqa

DEBUG = False

BASE_URL = ''

LOGGER_NAME = 'alerta'
LOG_FILE = None
LOG_MAX_BYTES = 100000
LOG_BACKUP_COUNT = 2
LOG_FORMAT = '%(asctime)s - %(name)s[%(process)d]: %(levelname)s - %(message)s [in %(pathname)s:%(lineno)d]'

SECRET_KEY = 'changeme'

QUERY_LIMIT = 1000
DEFAULT_PAGE_SIZE = QUERY_LIMIT  # maximum number of alerts returned by a single query
HISTORY_LIMIT = 100  # cap the number of alert history entries
HISTORY_ON_VALUE_CHANGE = True  # history entry for duplicate alerts if value changes

# MongoDB
MONGO_URI = 'mongodb://localhost:27017/monitoring'
MONGO_DATABASE = None  # can be used to override default database, above
MONGO_RAISE_ON_ERROR = True

# PostgreSQL
POSTGRES_URI = 'postgres://localhost:5432/monitoring'  # not used (use DATABASE_URL)
POSTGRES_DB = None

DATABASE_URL = MONGO_URI  # default: MongoDB
DATABASE_NAME = MONGO_DATABASE or POSTGRES_DB
DATABASE_RAISE_ON_ERROR = MONGO_RAISE_ON_ERROR  # True - terminate, False - ignore and continue

AUTH_REQUIRED = False
AUTH_PROVIDER = 'basic'  # basic (default), github, gitlab, google, keycloak, pingfederate, saml2
ADMIN_USERS = []  # type: List[str]
USER_DEFAULT_SCOPES = ['read', 'write']  # Note: 'write' scope implicitly includes 'read'
CUSTOMER_VIEWS = False

BASIC_AUTH_REALM = 'Alerta'
SIGNUP_ENABLED = True

OAUTH2_CLIENT_ID = None  # Google, GitHub or GitLab OAuth2 client ID and secret
OAUTH2_CLIENT_SECRET = None
ALLOWED_EMAIL_DOMAINS = ['*']

GITHUB_URL = None
ALLOWED_GITHUB_ORGS = ['*']

GITLAB_URL = 'https://gitlab.com'
ALLOWED_GITLAB_GROUPS = ['*']

LDAP_URL = ''  # eg. ldap://localhost:389
LDAP_DOMAINS = {}  # type: Dict[str, str]

KEYCLOAK_URL = None
KEYCLOAK_REALM = None
ALLOWED_KEYCLOAK_ROLES = ['*']

PINGFEDERATE_URL = None
PINGFEDERATE_OPENID_ACCESS_TOKEN_URL = PINGFEDERATE_URL
PINGFEDERATE_PUBKEY_LOCATION = None
PINGFEDERATE_TOKEN_ALGORITHM = None
PINGFEDERATE_OPENID_PAYLOAD_USERNAME = None
PINGFEDERATE_OPENID_PAYLOAD_EMAIL = None
PINGFEDERATE_OPENID_PAYLOAD_GROUP = None

SAML2_CONFIG = None
ALLOWED_SAML2_GROUPS = ['*']
SAML2_USER_NAME_FORMAT = '{givenName} {surname}'

TOKEN_EXPIRE_DAYS = 14
API_KEY_EXPIRE_DAYS = 365  # 1 year

CORS_ALLOW_HEADERS = ['Content-Type', 'Authorization', 'Access-Control-Allow-Origin']
CORS_ORIGINS = [
    # 'http://try.alerta.io',
    # 'http://explorer.alerta.io',
    'http://localhost',
    'http://localhost:8000',
    r'https?://\w*\.?local\.alerta\.io:?\d*/?.*'  # => http(s)://*.local.alerta.io:<port>
]
CORS_SUPPORTS_CREDENTIALS = AUTH_REQUIRED

SEVERITY_MAP = {
    'security': 0,
    'critical': 1,
    'major': 2,
    'minor': 3,
    'warning': 4,
    'indeterminate': 5,
    'cleared': 5,
    'normal': 5,
    'ok': 5,
    'informational': 6,
    'debug': 7,
    'trace': 8,
    'unknown': 9
}
DEFAULT_NORMAL_SEVERITY = 'normal'  # 'normal', 'ok', 'cleared'
DEFAULT_PREVIOUS_SEVERITY = 'indeterminate'

COLOR_MAP = {
    'severity': {
        'security': 'blue',
        'critical': 'red',
        'major': 'orange',
        'minor': 'yellow',
        'warning': '#1E90FF',
        'indeterminate': 'lightblue',
        'cleared': '#00CC00',
        'normal': '#00CC00',
        'ok': '#00CC00',
        'informational': '#00CC00',
        'debug': '#7554BF',
        'trace': '#7554BF',
        'unknown': 'silver'
    },
    'text': 'black',
    'highlight': 'skyblue '
}

DEFAULT_TIMEOUT = 86400
ALERT_TIMEOUT = DEFAULT_TIMEOUT
HEARTBEAT_TIMEOUT = DEFAULT_TIMEOUT

# Send verification emails to new BasicAuth users
EMAIL_VERIFICATION = False
SMTP_HOST = 'smtp.gmail.com'
SMTP_PORT = 587
MAIL_LOCALHOST = 'localhost'  # mail server to use in HELO/EHLO command
SMTP_STARTTLS = True
SMTP_USE_SSL = False
SSL_KEY_FILE = None
SSL_CERT_FILE = None
MAIL_FROM = 'your@gmail.com'  # replace with valid sender address
SMTP_USERNAME = ''  # application-specific username if different to MAIL_FROM user
SMTP_PASSWORD = ''  # password for MAIL_FROM (or SMTP_USERNAME if used)

GOOGLE_TRACKING_ID = None
AUTO_REFRESH_INTERVAL = 5000  # ms

# Plug-ins
PLUGINS = ['reject', 'blackout']
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
