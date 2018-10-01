
from importlib import import_module
from urllib.parse import urlparse

import psycopg2 as psycopg2

# http://stackoverflow.com/questions/8544983/dynamically-mixin-a-base-class-to-an-instance-in-python
from psycopg2.extras import NamedTupleCursor


class Base:
    pass


def get_backend(app):
    db_uri = app.config['DATABASE_URL']
    backend = urlparse(db_uri).scheme

    if backend == 'postgresql':
        backend = 'postgres'
    return backend


def load_backend(backend):
    try:
        return import_module('alerta.database.backends.%s' % backend)
    except Exception:
        raise ImportError('Failed to load %s database backend' % backend)


class Database(Base):

    def __init__(self, app=None):
        self.app = None
        if app is not None:
            self.init_db(app)

        self.conn = None
        self.cursor = None

    def init_db(self, app):
        backend = get_backend(app)
        cls = load_backend(backend)
        self.__class__ = type('DatabaseImpl', (cls.Backend, Database), {})

        try:
            self.create_engine(app, uri=app.config['DATABASE_URL'], dbname=app.config['DATABASE_NAME'])
        except Exception as e:
            if app.config['DATABASE_RAISE_ON_ERROR']:
                raise
            app.logger.warning(e)

        # app.before_request(self.get_db)
        # app.teardown_request(self.teardown_db)

    def create_engine(self, app, uri, dbname=None):
        raise NotImplementedError

    def get_alert(self, id, customers=None):
        raise NotImplementedError

