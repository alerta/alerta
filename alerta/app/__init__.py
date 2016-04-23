
import os
import sys
import logging

from flask import Flask
from flask.ext.cors import CORS

LOG_FORMAT = '%(asctime)s - %(name)s[%(process)d]: %(levelname)s - %(message)s'

app = Flask(__name__, static_url_path='')

app.config.from_object('alerta.settings')
app.config.from_pyfile('/etc/alertad.conf', silent=True)
app.config.from_envvar('ALERTA_SVR_CONF_FILE', silent=True)

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

if 'MAIL_FROM' in os.environ:
    app.config['MAIL_FROM'] = os.environ['MAIL_FROM']

if 'SMTP_PASSWORD' in os.environ:
    app.config['SMTP_PASSWORD'] = os.environ['SMTP_PASSWORD']

if 'CORS_ORIGINS' in os.environ:
    app.config['CORS_ORIGINS'] = os.environ['CORS_ORIGINS'].split(',')

if app.debug:
    app.debug_log_format = LOG_FORMAT
else:
    stderr_handler = logging.StreamHandler()
    stderr_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    app.logger.addHandler(stderr_handler)
    app.logger.setLevel(logging.INFO)

# Runtime config check
if app.config['CUSTOMER_VIEWS'] and not app.config['AUTH_REQUIRED']:
    raise RuntimeError('To use customer views you must enable authentication')

if app.config['CUSTOMER_VIEWS'] and not app.config['ADMIN_USERS']:
    raise RuntimeError('Customer views is enabled but there are no admin users')

cors = CORS(app)

from alerta.app.database import Mongo
db = Mongo()

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
