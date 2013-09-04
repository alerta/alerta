
import sys

from flask import Flask

from alerta.common import config
from alerta.common import log as logging

Version = '2.0.1'

LOG = logging.getLogger(__name__)
CONF = config.CONF

config.parse_args(sys.argv[1:], version=Version)
logging.setup('alerta')

app = Flask(__name__)
app.config.from_object(__name__)

import views
