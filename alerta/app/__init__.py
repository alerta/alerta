
import os
import sys
import logging

from flask import Flask
from flask_cors import CORS

from alerta.app.alert import DateEncoder

LOG_FORMAT = '%(asctime)s - %(name)s[%(process)d]: %(levelname)s - %(message)s [in %(pathname)s:%(lineno)d]'

app = Flask(__name__, static_url_path='')

app.json_encoder = DateEncoder

app.config.from_object('alerta.settings')
app.config.from_pyfile('/etc/alertad.conf', silent=True)
app.config.from_envvar('ALERTA_SVR_CONF_FILE', silent=True)

if 'DEBUG' in os.environ:
    app.debug = True

if 'BASE_URL' in os.environ:
    app.config['BASE_URL'] = os.environ['BASE_URL']

if 'SECRET_KEY' in os.environ:
    app.config['SECRET_KEY'] = os.environ['SECRET_KEY']

if 'AUTH_REQUIRED' in os.environ:
    app.config['AUTH_REQUIRED'] = True if os.environ['AUTH_REQUIRED'] == 'True' else False

if 'ADMIN_USERS' in os.environ:
    app.config['ADMIN_USERS'] = os.environ['ADMIN_USERS'].split(',')

if 'CUSTOMER_VIEWS' in os.environ:
    app.config['CUSTOMER_VIEWS'] = True if os.environ['CUSTOMER_VIEWS'] == 'True' else False

if 'OAUTH2_CLIENT_ID' in os.environ:
    app.config['OAUTH2_CLIENT_ID'] = os.environ['OAUTH2_CLIENT_ID']

if 'OAUTH2_CLIENT_SECRET' in os.environ:
    app.config['OAUTH2_CLIENT_SECRET'] = os.environ['OAUTH2_CLIENT_SECRET']

if 'ALLOWED_EMAIL_DOMAINS' in os.environ:
    app.config['ALLOWED_EMAIL_DOMAINS'] = os.environ['ALLOWED_EMAIL_DOMAINS'].split(',')

if 'ALLOWED_GITHUB_ORGS' in os.environ:
    app.config['ALLOWED_GITHUB_ORGS'] = os.environ['ALLOWED_GITHUB_ORGS'].split(',')

if 'GITLAB_URL' in os.environ:
    app.config['GITLAB_URL'] = os.environ['GITLAB_URL']

if 'ALLOWED_GITLAB_GROUPS' in os.environ:
    app.config['ALLOWED_GITLAB_GROUPS'] = os.environ['ALLOWED_GITLAB_GROUPS'].split(',')

if 'CORS_ORIGINS' in os.environ:
    app.config['CORS_ORIGINS'] = os.environ['CORS_ORIGINS'].split(',')

if 'MAIL_FROM' in os.environ:
    app.config['MAIL_FROM'] = os.environ['MAIL_FROM']

if 'SMTP_PASSWORD' in os.environ:
    app.config['SMTP_PASSWORD'] = os.environ['SMTP_PASSWORD']

if 'PLUGINS' in os.environ:
    app.config['PLUGINS'] = os.environ['PLUGINS'].split(',')

# Setup logging
from logging import getLogger
loggers = [app.logger, getLogger('werkzeug'), getLogger('requests'), getLogger('flask_cors')]

if app.debug:
    for logger in loggers:
        logger.setLevel(logging.DEBUG)

if app.config['LOG_FILE']:
    from logging.handlers import RotatingFileHandler
    del app.logger.handlers[:]
    logfile_handler = RotatingFileHandler(app.config['LOG_FILE'], maxBytes=100000, backupCount=2)
    logfile_handler.setLevel(logging.DEBUG)
    logfile_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    for logger in loggers:
        logger.addHandler(logfile_handler)

# Runtime config check
if app.config['CUSTOMER_VIEWS'] and not app.config['AUTH_REQUIRED']:
    raise RuntimeError('Must enable authentication to use customer views')

if app.config['CUSTOMER_VIEWS'] and not app.config['ADMIN_USERS']:
    raise RuntimeError('Customer views is enabled but there are no admin users')

cors = CORS(app)

from alerta.app.database.utils import Connection
conn = Connection()
db = conn.connect()

if sys.version_info[0] == 2:
    import views
    import webhooks.views
    import oembed.views
    import management.views
    import auth
else:
    from .views import *
    from .webhooks.views import *
    from .oembed.views import *
    from .management.views import *
    from .auth import *
