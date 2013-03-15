import sys

from flask import Flask
from flask.ext.pymongo import PyMongo

from alerta.common import config
from alerta.common import log as logging
from alerta.common.daemon import Daemon
from alerta.alert import Alert, Heartbeat
from alerta.common.mq import Messaging
from alerta.server.database import Mongo

Version = '2.0.0'

LOG = logging.getLogger(__name__)
CONF = config.CONF

config.parse_args(sys.argv[1:], version=Version)
logging.setup('alerta')

# Default configuration
#MONGO_HOST = CONF.mongo_host
#MONGO_PORT = CONF.mongo_port
#MONGO_DBNAME = CONF.mongo_db

app = Flask(__name__)
app.config.from_object(__name__)
#mongo = PyMongo(app)
db = Mongo()


import views
import management.views

