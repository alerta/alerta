
DEBUG = False
VERBOSE = False
USE_SYSLOG = True
USE_STDERR = False

LOG_FILE = 'alerta.log'
LOG_DIR = '/var/log'

SYSLOG_FACILITY = 'local7'

ENDPOINT = 'http://localhost:8080'

QUERY_LIMIT = 10000  # maximum number of alerts returned by a single query
HISTORY_LIMIT = 100  #

# MongoDB
MONGO_HOST = 'localhost'
MONGO_PORT = 27017
MONGO_DATABASE = 'monitoring'
MONGO_REPLSET = None  # 'alerta'

MONGO_USERNAME = 'alerta'
MONGO_PASSWORD = None


# Plugins
QUEUE = ''
TOPIC = 'notify'
TRANSPORTS = ['amqp', 'sns', 'logstash']

AMQP_URL = 'amqp://guest:guest@localhost:5672//'  # RabbitMQ
# AMQP_URL = 'mongodb://localhost:27017/kombu'    # MongoDB
# AMQP_URL = 'redis://localhost:6379/'            # Redis

AWS_ACCESS_KEY_ID = ''
AWS_SECRET_ACCESS_KEY = ''
REGION = 'eu-west-1'

