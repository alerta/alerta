import sys

from flask import Flask

from alerta.common import config
from alerta.common import log as logging
from alerta.common.mq import Messaging
from alerta.server.database import Mongo

Version = '2.0.0'

LOG = logging.getLogger(__name__)
CONF = config.CONF

config.parse_args(sys.argv[1:], version=Version)
logging.setup('alerta')


app = Flask(__name__)
app.config.from_object(__name__)
db = Mongo()

create_mq = Messaging()
create_mq.connect()

import views
import management.views

