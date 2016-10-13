#
# ***** ALERTA SERVER DEFAULT SETTINGS -- DO NOT MODIFY THIS FILE *****
#
# To override these settings use /etc/alertad.conf or the contents of the
# configuration file set by the environment variable ALERTA_SVR_CONF_FILE.
#
# Further information on settings can be found at http://docs.alerta.io

DEBUG = False

LOGGER_NAME = 'alerta'
LOG_FILE = None

SECRET_KEY = 'changeme'

QUERY_LIMIT = 10000  # maximum number of alerts returned by a single query
HISTORY_LIMIT = 100  # cap the number of alert history entries

# MongoDB
MONGO_HOST = 'localhost'
MONGO_PORT = 27017
MONGO_DATABASE = 'monitoring'
MONGO_REPLSET = None  # 'alerta'

MONGO_USERNAME = 'alerta'
MONGO_PASSWORD = None

AUTH_REQUIRED = False
ADMIN_USERS = []
CUSTOMER_VIEWS = False

OAUTH2_CLIENT_ID = None  # Google or GitHub OAuth2 client ID and secret
OAUTH2_CLIENT_SECRET = None
ALLOWED_EMAIL_DOMAINS = ['*']
ALLOWED_GITHUB_ORGS = ['*']

GITLAB_URL = None
ALLOWED_GITLAB_GROUPS = ['*']

TOKEN_EXPIRE_DAYS = 14
API_KEY_EXPIRE_DAYS = 365  # 1 year

# switches
AUTO_REFRESH_ALLOW = 'ON'  # set to 'OFF' to reduce load on API server by forcing clients to manually refresh
SENDER_API_ALLOW = 'ON'    # set to 'OFF' to block clients from sending new alerts to API server

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
DEFAULT_SEVERITY = 'indeterminate'

BLACKOUT_DURATION = 3600  # default period = 1 hour

EMAIL_VERIFICATION = False
SMTP_HOST = 'smtp.gmail.com'
SMTP_PORT = 587
MAIL_FROM = 'your@gmail.com'  # replace with valid sender address
SMTP_PASSWORD = ''  # password for MAIL_FROM account, Gmail uses application-specific passwords

# Plug-ins
PLUGINS = ['reject']

ORIGIN_BLACKLIST = []  # reject all foo alerts from bar, and everything from qux
#ORIGIN_BLACKLIST = ['foo/bar$', '.*/qux']  # reject all foo alerts from bar, and everything from qux
ALLOWED_ENVIRONMENTS = ['Production', 'Development']  # reject alerts without allowed environments
