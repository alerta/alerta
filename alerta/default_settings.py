#
# DO NOT MODIFY THIS FILE
#

DEBUG = True

SECRET_KEY = '0Afk\(,8$cr(Y8:MA""knd>[@$U[G.eQL6DjAmVs'

USE_STDERR = False

LOG_FILE = '/var/log/alerta.log'
LOG_FORMAT = '%(asctime)s %(name)s[%(process)d] %(threadName)s %(levelname)s - %(message)s [in %(pathname)s:%(lineno)d]'

USE_SYSLOG = False
SYSLOG_SOCKET = '/dev/log'  # Linux = /dev/log, Mac OSX = /var/run/syslog
SYSLOG_FACILITY = 'local7'

QUERY_LIMIT = 10000  # maximum number of alerts returned by a single query
HISTORY_LIMIT = 100  #

# MongoDB
MONGO_HOST = 'localhost'
MONGO_PORT = 27017
MONGO_DATABASE = 'monitoring'
MONGO_REPLSET = None  # 'alerta'

MONGO_USERNAME = 'alerta'
MONGO_PASSWORD = None

AUTH_REQUIRED = False
OAUTH2_CLIENT_ID = 'INSERT-OAUTH2-CLIENT-ID-HERE'  # required for access token validation
ALLOWED_EMAIL_DOMAINS = ['gmail.com']
ACCESS_TOKEN_CACHE_MINS = 60
API_KEY_EXPIRE_DAYS = 365

# AWS Credentials
AWS_ACCESS_KEY_ID = ''
AWS_SECRET_ACCESS_KEY = ''
AWS_REGION = 'eu-west-1'

# AMQP Credentials
AMQP_URL = 'amqp://guest:guest@localhost:5672//'  # RabbitMQ
# AMQP_URL = 'mongodb://localhost:27017/kombu'    # MongoDB
# AMQP_URL = 'redis://localhost:6379/'            # Redis

# Inbound
AWS_SQS_QUEUE = 'alerts'
AMQP_QUEUE = 'alerts'

# Plugins
PLUGINS = ['amqp', 'sns', 'logstash']

# Outbound
AMQP_TOPIC = 'notify'
AWS_SNS_TOPIC = 'notify'

# Logstash
LOGSTASH_HOST = 'localhost'
LOGSTASH_PORT = 6379

