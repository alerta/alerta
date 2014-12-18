
import os
import logging

from flask import Flask

import alerta

LOG_FORMAT = '%(asctime)s - %(name)s[%(process)d]: %(levelname)s - %(message)s'

app = Flask(__name__)

app.config.from_object('alerta.settings')
app.config.from_pyfile('/etc/alertad.conf', silent=True)
app.config.from_envvar('ALERTA_SVR_CONF_FILE', silent=True)

if 'SECRET_KEY' in os.environ:
    app.config['SECRET_KEY'] = os.environ['SECRET_KEY']

if app.debug:
    app.debug_log_format = LOG_FORMAT
else:
    stderr_handler = logging.StreamHandler()
    stderr_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    app.logger.addHandler(stderr_handler)
    app.logger.setLevel(logging.INFO)

app.logger.info('Starting alerta version %s ...', alerta.version)

from alerta.app.database import Mongo
db = Mongo()

import views
import webhooks.views
import management.views


def main():
    app.run(host='0.0.0.0', port=8080)

