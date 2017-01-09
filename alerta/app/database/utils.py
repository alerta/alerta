
from importlib import import_module

from alerta.app import app


def load_backend(backend):

    try:
        return import_module('alerta.app.database.%s' % backend)
    except:
        raise


class Connection(object):

    def connect(self):

        backend = load_backend(app.config['DATABASE_ENGINE'])
        return backend.Database()
