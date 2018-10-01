from datetime import datetime

import psycopg2
from flask import current_app
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
        select = """
            SELECT * FROM alerts
             WHERE (id ~* (%(id)s) OR last_receive_id ~* (%(id)s))
               AND {customer}
        """.format(customer='customer=ANY(%(customers)s)' if customers else '1=1')
        foo = self._fetchone(select, {'id': '^' + id, 'customers': customers})
        print(foo)
        return foo

    def _fetchone(self, query, vars):
        """
        Return none or one row.
        """
        cursor = self.conn.cursor()
        current_app.logger.warning(cursor, query, vars)
        cursor.execute(query, vars)
        return cursor.fetchone()
