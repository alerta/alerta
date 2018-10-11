from typing import Any, Dict

from flask import Flask
from flask_compress import Compress
from flask_cors import CORS
from raven.contrib.flask import Sentry

from alerta.database.base import Database, QueryBuilder
from alerta.exceptions import ExceptionHandlers
from alerta.models.alarms import AlarmModel
from alerta.utils.config import Config
from alerta.utils.key import ApiKeyHelper
from alerta.utils.mailer import Mailer
from alerta.utils.plugin import Plugins
from alerta.utils.webhook import CustomWebhooks

config = Config()
alarm_model = AlarmModel()

cors = CORS()
compress = Compress()
handlers = ExceptionHandlers()
key_helper = ApiKeyHelper()

db = Database()
qb = QueryBuilder()
sentry = Sentry()
mailer = Mailer()
plugins = Plugins()
custom_webhooks = CustomWebhooks()


def create_app(config_override: Dict[str, Any]=None, environment: str=None) -> Flask:
    app = Flask(__name__)
    app.config['ENVIRONMENT'] = environment
    config.init_app(app)
    app.config.update(config_override or {})

    alarm_model.init_app(app)

    cors.init_app(app)
    compress.init_app(app)
    handlers.register(app)
    key_helper.init_app(app)

    db.init_db(app)
    qb.init_app(app)
    sentry.init_app(app)

    mailer.register(app)
    plugins.register(app)
    custom_webhooks.register(app)

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

    return app


try:
    from celery import Celery
except ImportError:
    pass


def create_celery_app(app: Flask=None) -> 'Celery':

    from alerta.utils.format import register_custom_serializer
    register_custom_serializer()

    app = app or create_app()
    celery = Celery(
        app.name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):  # type: ignore
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery
