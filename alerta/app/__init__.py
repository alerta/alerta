
import os
import logging

from flask import Flask

app = Flask(__name__)
app.config.from_object('alerta.settings')
app.config.from_pyfile('/etc/alertad.conf', silent=True)
app.config.from_envvar('ALERTA_SVR_CONF_FILE', silent=True)

if 'SECRET_KEY' in os.environ:
    app.config['SECRET_KEY'] = os.environ['SECRET_KEY']

if not app.debug:
    app.logger.addHandler(logging.StreamHandler())
    app.logger.setLevel(logging.INFO)

from alerta.app.database import Mongo
db = Mongo()

import views
import management.views


def main():
    app.run(host='0.0.0.0', port=8080, debug=True)