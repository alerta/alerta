
import os
import sys
import logging

from logging.handlers import RotatingFileHandler, SysLogHandler
from flask import Flask

app = Flask(__name__)
app.config.from_object('alerta.settings')
app.config.from_pyfile('/etc/alertad.conf', silent=True)
app.config.from_envvar('ALERTA_SVR_CONF_FILE', silent=True)

if 'SECRET_KEY' in os.environ:
    app.config['SECRET_KEY'] = os.environ['SECRET_KEY']

if app.config['USE_STDERR']:
    stderr_hanlder = logging.StreamHandler()
    stderr_hanlder.setFormatter(logging.Formatter(fmt=app.config['LOG_FORMAT']))
    app.logger.addHandler(stderr_hanlder)

if app.config['LOG_FILE']:
    file_handler = RotatingFileHandler(filename=app.config['LOG_FILE'], encoding='utf-8', maxBytes=10000, backupCount=1)
    file_handler.setFormatter(logging.Formatter(fmt=app.config['LOG_FORMAT']))
    app.logger.addHandler(file_handler)

if app.config['USE_SYSLOG']:
    syslog_handler = SysLogHandler(address=app.config['SYSLOG_SOCKET'], facility=app.config['SYSLOG_FACILITY'])
    syslog_handler.setFormatter(logging.Formatter(fmt=app.config['LOG_FORMAT']))
    app.logger.addHandler(syslog_handler)

if app.debug:
    app.logger.setLevel(logging.DEBUG)
else:
    app.logger.setLevel(logging.WARNING)

from alerta.app.database import Mongo
db = Mongo()

import views
import management.views


def main():
    app.run(host='0.0.0.0', port=8080, debug=True)