
from flask import Flask
from flask_compress import Compress
from flask_cors import CORS
from raven.contrib.flask import Sentry

from alerta.database.base import Database, QueryBuilder
from alerta.exceptions import ExceptionHandlers
from alerta.models.severity_code import Severity
from alerta.plugins import Plugins
from alerta.utils.config import Config
from alerta.utils.key import ApiKeyHelper

config = Config()
severity = Severity()

cors = CORS()
compress = Compress()
handlers = ExceptionHandlers()
key_helper = ApiKeyHelper()

db = Database()
qb = QueryBuilder()
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
    qb.init_app(app)
    sentry.init_app(app)

    from alerta.utils.format import CustomJSONEncoder
    app.json_encoder = CustomJSONEncoder

    from alerta.views import api
    app.register_blueprint(api)

    from alerta.webhooks import webhooks
    app.register_blueprint(webhooks)

    from alerta.auth import auth
    app.register_blueprint(auth)

    from alerta.management import mgmt
    app.register_blueprint(mgmt)

    plugins.register(app)

    return app
