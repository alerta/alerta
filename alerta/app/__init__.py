
import os
import logging

from flask import Flask
from flask.ext.cors import CORS

from alerta.version import __version__

LOG_FORMAT = '%(asctime)s - %(name)s[%(process)d]: %(levelname)s - %(message)s'

app = Flask(__name__, static_url_path='')

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

cors = CORS(app)

app.logger.info('Starting alerta version %s ...', __version__)

from alerta.app.database import Mongo
db = Mongo()

import views
import webhooks.views
import oembed.views
import management.views
import auth


def main():
    app.run(host='0.0.0.0', port=8080, processes=3)

