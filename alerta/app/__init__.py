from flask import Flask
from flask_compress import Compress
from flask_cors import CORS
from raven.contrib.flask import Sentry

from alerta.app.config import Config
from alerta.app.utils.key import ApiKeyHelper
from alerta.app.models.severity_code import Severity
from alerta.app.database.base import Database
from alerta.app.exceptions import ExceptionHandlers
from alerta.plugins import Plugins

config = Config()
severity = Severity()

cors = CORS()
compress = Compress()
handlers = ExceptionHandlers()
key_helper = ApiKeyHelper()

db = Database()
sentry = Sentry()
plugins = Plugins()


def create_app(config_override=None, environment=None):
    app = Flask(__name__)
    app.config['ENVIRONMENT'] = environment
    config.init_app(app)
    app.config.update(config_override or {})

    severity.init_app(app)
    key_helper.init_app(app)

    cors.init_app(app)
    compress.init_app(app)
    handlers.register(app)

    db.init_db(app)
    sentry.init_app(app)

    from alerta.app.utils.format import DateEncoder
    app.json_encoder = DateEncoder

    from alerta.app.views import api
    app.register_blueprint(api)

    from alerta.app.webhooks import webhooks
    app.register_blueprint(webhooks)

    from alerta.app.auth import auth
    app.register_blueprint(auth)

    from alerta.app.management import mgmt
    app.register_blueprint(mgmt)

    from alerta.app import plugins
    plugins.register(app)

    return app
