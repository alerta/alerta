
import os

from importlib import import_module

from flask import g


class Base(object):
    pass

# http://stackoverflow.com/questions/8544983/dynamically-mixin-a-base-class-to-an-instance-in-python


class Database(Base):

    def __init__(self, app=None):
        self.app = None
        if app is not None:
            self.init_db(app)

    def init_db(self, app):
        backend = os.environ.get('DATABASE_ENGINE', None) or app.config['DATABASE_ENGINE']
        cls = load_backend(backend)
        self.__class__ = type('DatabaseImpl', (cls.Backend, Database), {})

        self.create_engine(dsn=app.config['DATABASE_DSN'], dbname=app.config['DATABASE_NAME'])

        app.before_request(self.before_request)
        app.teardown_request(self.teardown_request)

    def create_engine(self, dsn, dbname=None):
        raise NotImplementedError('database engine has no create_engine() method')

    def connect(self):
        raise NotImplementedError('database engine has no connect() method')

    def close(self):
        raise NotImplementedError('database engine has no close() method')

    def destroy(self):
        raise NotImplementedError('database engine has no destroy() method')

    def build_query(self, params):
        raise NotImplementedError('database engine has no build_query() method')

    def before_request(self):
        g.db = self.connect()

    def after_request(self):
        pass

    def teardown_request(self, exc):
        db = getattr(g, 'db', None)
        if db is not None:
            self.close()


def load_backend(backend):
    try:
        return import_module('alerta.app.database.backends.%s' % backend)
    except:
        raise ImportError('Failed to load %s database backend' % backend)
