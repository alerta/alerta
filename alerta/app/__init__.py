
import logging

from flask import Flask

LOG = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_object('alerta.default_settings')
app.config.from_object('alerta.settings')

from logging.handlers import SysLogHandler
syslog_handler = SysLogHandler(address='/var/run/syslog', facility='local7')
app.logger.addHandler(syslog_handler)

from alerta.app.database import Mongo
db = Mongo()

import views
import management.views
