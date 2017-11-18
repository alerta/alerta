
from importlib import import_module

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

from flask import g

# http://stackoverflow.com/questions/8544983/dynamically-mixin-a-base-class-to-an-instance-in-python


class Base(object):
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
    except:
        raise ImportError('Failed to load %s database backend' % backend)


class Database(Base):

    def __init__(self, app=None):
        self.app = None
        if app is not None:
            self.init_db(app)

    def init_db(self, app):
        backend = get_backend(app)
        cls = load_backend(backend)
        self.__class__ = type('DatabaseImpl', (cls.Backend, Database), {})

        self.create_engine(app, uri=app.config['DATABASE_URL'], dbname=app.config['DATABASE_NAME'])

        app.before_request(self.before_request)
        app.teardown_request(self.teardown_request)

    def create_engine(self, app, uri, dbname=None):
        raise NotImplementedError('Database engine has no create_engine() method')

    def connect(self):
        raise NotImplementedError('Database engine has no connect() method')

    @property
    def name(self):
        raise NotImplementedError

    @property
    def version(self):
        raise NotImplementedError

    @property
    def is_alive(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError('Database engine has no close() method')

    def destroy(self):
        raise NotImplementedError('Database engine has no destroy() method')

    def before_request(self):
        g.db = self.connect()

    def after_request(self):
        pass

    def teardown_request(self, exc):
        db = getattr(g, 'db', None)
        if db is not None:
            self.close()

    #### ALERTS

    def get_severity(self, alert):
        raise NotImplementedError

    def get_status(self, alert):
        raise NotImplementedError

    def is_duplicate(self, alert):
        raise NotImplementedError

    def is_correlated(self, alert):
        raise NotImplementedError

    def is_flapping(self, alert, window=1800, count=2):
        raise NotImplementedError

    def dedup_alert(self, alert, history):
        raise NotImplementedError

    def correlate_alert(self, alert, history):
        raise NotImplementedError

    def create_alert(self, alert):
        raise NotImplementedError

    def get_alert(self, id, customer=None):
        raise NotImplementedError

    #### STATUS, TAGS, ATTRIBUTES

    def set_status(self, id, status, history=None):
        raise NotImplementedError

    def tag_alert(self, id, tags):
        raise NotImplementedError

    def untag_alert(self, id, tags):
        raise NotImplementedError

    def update_attributes(self, id, old_attrs, new_attrs):
        raise NotImplementedError

    def delete_alert(self, id):
        raise NotImplementedError

    #### SEARCH & HISTORY

    def get_alerts(self, query=None, page=None, page_size=None):
        raise NotImplementedError

    def get_history(self, query=None, page=None, page_size=None):
        raise NotImplementedError

    #### COUNTS

    def get_count(self, query=None):
        raise NotImplementedError

    def get_counts(self, query=None, group=None):
        raise NotImplementedError

    def get_counts_by_severity(self, query=None):
        raise NotImplementedError

    def get_counts_by_status(self, query=None):
        raise NotImplementedError

    def get_topn_count(self, query, group="event", topn=10):
        raise NotImplementedError

    def get_topn_flapping(self, query, group="event", topn=10):
        raise NotImplementedError

    #### ENVIRONMENTS

    def get_environments(self, query=None, topn=100):
        raise NotImplementedError

    #### SERVICES

    def get_services(self, query=None, topn=100):
        raise NotImplementedError

    #### TAGS

    def get_tags(self, query=None, topn=100):
        raise NotImplementedError

    #### BLACKOUTS

    def create_blackout(self, blackout):
        raise NotImplementedError

    def get_blackout(self, id, customer=None):
        raise NotImplementedError

    def get_blackouts(self, query=None):
        raise NotImplementedError

    def is_blackout_period(self, alert):
        raise NotImplementedError

    def delete_blackout(self, id):
        raise NotImplementedError

    #### HEARTBEATS

    def upsert_heartbeat(self, heartbeat):
        raise NotImplementedError

    def get_heartbeat(self, id, customer=None):
        raise NotImplementedError

    def get_heartbeats(self, query=None):
        raise NotImplementedError

    def delete_heartbeat(self, id):
        raise NotImplementedError

    #### API KEYS

    def create_key(self, key):
        raise NotImplementedError

    def get_key(self, key):
        raise NotImplementedError

    def get_keys(self, query=None):
        raise NotImplementedError

    def update_key_last_used(self, key):
        raise NotImplementedError

    def delete_key(self, key):
        raise NotImplementedError

    #### USERS

    def create_user(self, user):
        raise NotImplementedError

    def get_user(self, id):
        raise NotImplementedError

    def get_users(self, query=None):
        raise NotImplementedError

    def get_user_by_email(self, email):
        raise NotImplementedError

    def get_user_by_hash(self, hash):
        raise NotImplementedError

    def update_last_login(self, id):
        raise NotImplementedError

    def set_email_hash(self, id, hash):
        raise NotImplementedError

    def update_user(self, id, **kwargs):
        raise NotImplementedError

    def update_user_attributes(self, id, old_attrs, new_attrs):
        raise NotImplementedError

    def delete_user(self, id):
        raise NotImplementedError

    #### PERMISSIONS

    def create_perm(self, perm):
        raise NotImplementedError

    def get_perm(self, id):
        raise NotImplementedError

    def get_perms(self, query=None):
        raise NotImplementedError

    def delete_perm(self, id):
        raise NotImplementedError

    def get_scopes_by_match(self, login, matches):
        raise NotImplementedError

    #### CUSTOMERS

    def create_customer(self, customer):
        raise NotImplementedError

    def get_customer(self, id):
        raise NotImplementedError

    def get_customers(self, query=None):
        raise NotImplementedError

    def delete_customer(self, id):
        raise NotImplementedError

    def get_customers_by_match(self, login, matches):
        raise NotImplementedError

    #### METRICS

    def get_metrics(self, type=None):
        raise NotImplementedError

    def set_gauge(self, gauge):
        raise NotImplementedError

    def inc_counter(self, counter):
        raise NotImplementedError

    def update_timer(self, timer):
        raise NotImplementedError

    #### HOUSEKEEPING

    def housekeeping(self, expired_threshold, info_threshold):
        raise NotImplementedError


class QueryBuilder(Base):

    def __init__(self, app=None):
        self.app = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        backend = get_backend(app)
        cls = load_backend(backend)
        self.__class__ = type('QueryBuilderImpl', (cls.QueryBuilderImpl, QueryBuilder), {})

    @staticmethod
    def from_params(params, query_time=None):
        raise NotImplementedError('QueryBuilder has no from_params() method')

    @staticmethod
    def from_dict(d, query_time=None):
        raise NotImplementedError('QueryBuilder has no from_dict() method')
