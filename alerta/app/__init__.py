
import logging

from logging.handlers import RotatingFileHandler, SysLogHandler
from flask import Flask

app = Flask(__name__)
app.config.from_object('alerta.default_settings')
app.config.from_object('alerta.settings')

if app.config['LOG_FILE']:
    file_handler = RotatingFileHandler(filename=app.config['LOG_FILE'], maxBytes=10000, backupCount=1)
    file_handler.setFormatter(logging.Formatter(fmt=app.config['LOG_FORMAT']))
    app.logger.addHandler(file_handler)

if app.config['USE_SYSLOG']:
    syslog_handler = SysLogHandler(address=app.config['SYSLOG_SOCKET'], facility=app.config['SYSLOG_FACILITY'])
    syslog_handler.setFormatter(logging.Formatter(fmt=app.config['LOG_FORMAT']))
    app.logger.addHandler(syslog_handler)

if app.debug:
    app.logger.setLevel(logging.DEBUG)

from alerta.app.database import Mongo

db = Mongo()

import views
import management.views
