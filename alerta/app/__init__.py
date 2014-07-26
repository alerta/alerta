
from flask import Flask

from alerta.common import log as logging
from alerta.app.database import Mongo

LOG = logging.getLogger(__name__)

logging.setup('alerta')

app = Flask(__name__)
app.config.from_object(__name__)
db = Mongo()

import views
import management.views
