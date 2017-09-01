#
# ***** ALERTA SERVER DEFAULT SETTINGS -- DO NOT MODIFY THIS FILE *****
#
# To override these settings use /etc/alertad.conf or the contents of the
# configuration file set by the environment variable ALERTA_SVR_CONF_FILE.
#
# Further information on settings can be found at http://docs.alerta.io

DEBUG = False

BASE_URL = ''
LOGGER_NAME = 'alerta'
LOG_FILE = None
LOG_FORMAT = '%(asctime)s - %(name)s[%(process)d]: %(levelname)s - %(message)s [in %(pathname)s:%(lineno)d]'

SECRET_KEY = 'changeme'

QUERY_LIMIT = 1000
DEFAULT_PAGE_SIZE = QUERY_LIMIT  # maximum number of alerts returned by a single query
HISTORY_LIMIT = 100  # cap the number of alert history entries

# MongoDB
MONGO_URI = 'mongodb://localhost:27017/monitoring'
MONGO_DATABASE = None  # can be used to override default database, above

# Postgres
# DATABASE_DSN = 'postgresql://localhost:5432/monitoring'

# Database backend (default: mongodb)
DATABASE_ENGINE = 'mongodb'
DATABASE_DSN = MONGO_URI
DATABASE_NAME = MONGO_DATABASE

AUTH_REQUIRED = False
ADMIN_USERS = []
USER_DEFAULT_SCOPES = ['read', 'write']  # Note: 'write' scope implicitly includes 'read'
CUSTOMER_VIEWS = False

OAUTH2_CLIENT_ID = None  # Google or GitHub OAuth2 client ID and secret
OAUTH2_CLIENT_SECRET = None
ALLOWED_EMAIL_DOMAINS = ['*']

GITHUB_URL = None
ALLOWED_GITHUB_ORGS = ['*']

GITLAB_URL = 'https://gitlab.com'
ALLOWED_GITLAB_GROUPS = ['*']

KEYCLOAK_URL = None
KEYCLOAK_REALM = None
ALLOWED_KEYCLOAK_ROLES = ['*']

# FIXME: Add SAML default config

TOKEN_EXPIRE_DAYS = 14
API_KEY_EXPIRE_DAYS = 365  # 1 year

CORS_ALLOW_HEADERS = ['Content-Type', 'Authorization', 'Access-Control-Allow-Origin']
CORS_ORIGINS = [
    'http://try.alerta.io',
    'http://explorer.alerta.io',
    'http://localhost'
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

DEFAULT_TIMEOUT = 86400
DEFAULT_ALERT_TIMEOUT = DEFAULT_TIMEOUT
DEFAULT_HEARTBEAT_TIMEOUT = DEFAULT_TIMEOUT

BLACKOUT_DURATION = 3600  # default period = 1 hour

EMAIL_VERIFICATION = False
SMTP_HOST = 'smtp.gmail.com'
SMTP_PORT = 587
MAIL_FROM = 'your@gmail.com'  # replace with valid sender address
SMTP_PASSWORD = ''  # password for MAIL_FROM account, Gmail uses application-specific passwords

# Plug-ins
PLUGINS = ['reject', 'blackout']

ORIGIN_BLACKLIST = []
#ORIGIN_BLACKLIST = ['foo/bar$', '.*/qux']  # reject all foo alerts from bar, and everything from qux
ALLOWED_ENVIRONMENTS = ['Production', 'Development']  # reject alerts without allowed environments
