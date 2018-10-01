from datetime import datetime

import psycopg2
from psycopg2.extensions import AsIs, adapt, register_adapter
from psycopg2.extras import NamedTupleCursor

from alerta.database.base import Database
from alerta.exceptions import NoCustomerMatch
from alerta.utils.api import absolute_url
from alerta.utils.format import DateTime

MAX_RETRIES = 5


class Backend(Database):

    def create_engine(self, app, uri, dbname=None):
        self.uri = uri
        self.dbname = dbname

        self.conn = self.connect()

        with app.open_resource('sql/schema.sql') as f:
            self.conn.cursor().execute(f.read())
            self.conn.commit()

        # register_adapter(dict, Json)
        # register_adapter(datetime, self._adapt_datetime)
        # register_composite(
        #     'history',
        #     conn,
        #     globally=True
        # )
        # from alerta.models.alert import History
        # register_adapter(History, HistoryAdapter)

    def connect(self):
        conn = psycopg2.connect(
            dsn=self.uri,
            dbname=self.dbname,
            cursor_factory=NamedTupleCursor
        )
        return conn

    def get_alert(self, id, customers=None):
        print(self.conn)
        print(self.cursor)

        
