
from flask import Flask

from alerta.common import config
from alerta.common import log as logging
from alerta.common.amqp import Messaging, FanoutPublisher
from alerta.app.database import Mongo

__version__ = '3.0.2'

LOG = logging.getLogger(__name__)
CONF = config.CONF

config.parse_args(version=__version__)
logging.setup('alerta')

app = Flask(__name__)
app.config.from_object(__name__)
db = Mongo()

mq = Messaging()
notify = FanoutPublisher(mq.channel)

import views
import management.views
