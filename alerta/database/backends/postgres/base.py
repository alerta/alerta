from collections import namedtuple
from datetime import datetime, timedelta

import psycopg2
from flask import current_app, g
from psycopg2.extensions import register_adapter, adapt, AsIs
from psycopg2.extras import NamedTupleCursor, register_composite, Json

from alerta.database.base import Database
from alerta.exceptions import NoCustomerMatch
from alerta.utils.api import absolute_url
from alerta.utils.format import DateTime
from .utils import Query


def adapt_history(h):
    return AsIs("(%s, %s, %s, %s, %s, %s, %s, %s)::history" % (
        adapt(h.id).getquoted().decode('utf-8'),
        adapt(h.event).getquoted().decode('utf-8'),
        adapt(h.severity).getquoted().decode('utf-8'),
        adapt(h.status).getquoted().decode('utf-8'),
        adapt(h.value).getquoted().decode('utf-8'),
        adapt(h.text).getquoted().decode('utf-8'),
        adapt(h.change_type).getquoted().decode('utf-8'),
        adapt(h.update_time).getquoted().decode('utf-8')
    ))


class Backend(Database):

    def create_engine(self, app, uri, dbname=None):
        self.uri = uri
        self.dbname = dbname

        conn = self.connect()
        with app.open_resource('sql/schema.sql') as f:
            conn.cursor().execute(f.read())
            conn.commit()

        register_adapter(dict, Json)
        register_adapter(datetime, self._adapt_datetime)
        register_composite(
            'history',
            conn,
            globally=True
        )
        from alerta.models.alert import History
        register_adapter(History, adapt_history)

    def connect(self):
        # > createdb alerta
        conn = psycopg2.connect(
            dsn=self.uri,
            dbname=self.dbname,
            cursor_factory=NamedTupleCursor
        )
        conn.set_client_encoding('UTF8')
        return conn

    @staticmethod
    def _adapt_datetime(dt):
        return AsIs("%s" % adapt(DateTime.iso8601(dt)))

    @property
    def name(self):
        cursor = g.db.cursor()
        cursor.execute("SELECT current_database()")
        return cursor.fetchone()[0]

    @property
    def version(self):
        cursor = g.db.cursor()
        cursor.execute("SHOW server_version")
        return cursor.fetchone()[0]

    @property
    def is_alive(self):
        cursor = g.db.cursor()
        cursor.execute("SELECT true")
        return cursor.fetchone()

    def close(self):
        g.db.close()

    def destroy(self):
        conn = self.connect()
        cursor = conn.cursor()
        for table in ['alerts', 'blackouts', 'customers', 'heartbeats', 'keys', 'metrics', 'perms', 'users']:
            cursor.execute("DROP TABLE IF EXISTS %s" % table)
        conn.commit()
        conn.close()

    #### ALERTS

    def get_severity(self, alert):
        select = """
            SELECT severity FROM alerts
             WHERE environment=%(environment)s AND resource=%(resource)s
               AND ((event=%(event)s AND severity!=%(severity)s)
                OR (event!=%(event)s AND %(event)s=ANY(correlate)))
               AND customer IS NOT DISTINCT FROM %(customer)s
            """
        return self._fetchone(select, vars(alert)).severity

    def get_status(self, alert):
        select = """
            SELECT status FROM alerts
             WHERE environment=%(environment)s AND resource=%(resource)s
              AND (event=%(event)s OR %(event)s=ANY(correlate))
              AND customer IS NOT DISTINCT FROM %(customer)s
            """
        return self._fetchone(select, vars(alert)).status

    def is_duplicate(self, alert):
        select = """
            SELECT id FROM alerts
             WHERE environment=%(environment)s
               AND resource=%(resource)s
               AND event=%(event)s
               AND severity=%(severity)s
               AND customer IS NOT DISTINCT FROM %(customer)s
            """
        return bool(self._fetchone(select, vars(alert)))

    def is_correlated(self, alert):
        select = """
            SELECT id FROM alerts
             WHERE environment=%(environment)s AND resource=%(resource)s
               AND ((event=%(event)s AND severity!=%(severity)s)
                OR (event!=%(event)s AND %(event)s=ANY(correlate)))
               AND customer IS NOT DISTINCT FROM %(customer)s
        """
        return bool(self._fetchone(select, vars(alert)))

    def is_flapping(self, alert, window=1800, count=2):
        select = """
            SELECT COUNT(*)
              FROM alerts, unnest(history) h
             WHERE environment=%(environment)s
               AND resource=%(resource)s
               AND event=%(event)s
               AND h.update_time > {window}
               AND h.type="severity"
               AND customer IS NOT DISTINCT FROM %(customer)s
        """.format(window=(datetime.utcnow() - timedelta(seconds=window)))
        return self._fetchone(select, vars(alert)).count > count

    def dedup_alert(self, alert, history):
        """
        Update alert value, text and rawData, increment duplicate count and set repeat=True, and
        keep track of last receive id and time but don't append to history unless status changes.
        """
        update = """
            UPDATE alerts
               SET status=%(status)s, value=%(value)s, text=%(text)s, raw_data=%(raw_data)s, repeat=%(repeat)s,
                   last_receive_id=%(last_receive_id)s, last_receive_time=%(last_receive_time)s,
                   tags=ARRAY(SELECT DISTINCT UNNEST(tags || %(tags)s)), attributes=attributes || %(attributes)s,
                   duplicate_count=duplicate_count+1, history=(history || %(history)s)[1:{limit}]
             WHERE environment=%(environment)s
               AND resource=%(resource)s
               AND event=%(event)s
               AND severity=%(severity)s
               AND customer IS NOT DISTINCT FROM %(customer)s
         RETURNING *
        """.format(limit=current_app.config['HISTORY_LIMIT'])
        return self._update(update, vars(alert), returning=True)

    def correlate_alert(self, alert, history):
        alert.history = history
        update = """
            UPDATE alerts
               SET event=%(event)s, severity=%(severity)s, status=%(status)s, value=%(value)s, text=%(text)s,
                   create_time=%(create_time)s, raw_data=%(raw_data)s, duplicate_count=%(duplicate_count)s,
                   repeat=%(repeat)s, previous_severity=%(previous_severity)s, trend_indication=%(trend_indication)s,
                   receive_time=%(receive_time)s, last_receive_id=%(last_receive_id)s,
                   last_receive_time=%(last_receive_time)s, tags=ARRAY(SELECT DISTINCT UNNEST(tags || %(tags)s)),
                   attributes=attributes || %(attributes)s, history=(history || %(history)s)[1:{limit}]
             WHERE environment=%(environment)s
               AND resource=%(resource)s
               AND ((event=%(event)s AND severity!=%(severity)s) OR (event!=%(event)s AND %(event)s=ANY(correlate)))
               AND customer IS NOT DISTINCT FROM %(customer)s
         RETURNING *
        """.format(limit=current_app.config['HISTORY_LIMIT'])
        return self._update(update, vars(alert), returning=True)

    def create_alert(self, alert):
        insert = """
            INSERT INTO alerts (id, resource, event, environment, severity, correlate, status, service, "group",
                value, text, tags, attributes, origin, type, create_time, timeout, raw_data, customer,
                duplicate_count, repeat, previous_severity, trend_indication, receive_time, last_receive_id,
                last_receive_time, history)
            VALUES (%(id)s, %(resource)s, %(event)s, %(environment)s, %(severity)s, %(correlate)s, %(status)s,
                %(service)s, %(group)s, %(value)s, %(text)s, %(tags)s, %(attributes)s, %(origin)s,
                %(event_type)s, %(create_time)s, %(timeout)s, %(raw_data)s, %(customer)s, %(duplicate_count)s,
                %(repeat)s, %(previous_severity)s, %(trend_indication)s, %(receive_time)s, %(last_receive_id)s,
                %(last_receive_time)s, %(history)s::history[])
            RETURNING *
        """
        return self._insert(insert, vars(alert))

    def get_alert(self, id, customer=None):
        select = """
            SELECT * FROM alerts
             WHERE id ~* (%(id)s) OR last_receive_id ~* (%(id)s)
               AND customer IS NOT DISTINCT FROM %(customer)s
        """
        return self._fetchone(select, {'id': '^'+id, 'customer': customer})

    #### STATUS, TAGS, ATTRIBUTES

    def set_status(self, id, status, history=None):
        update = """
            UPDATE alerts
            SET status=%(status)s, history=(history || %(change)s)[1:{limit}]
            WHERE id=%(id)s OR id LIKE %(like_id)s
            RETURNING *
        """.format(limit=current_app.config['HISTORY_LIMIT'])
        return self._update(update, {'id': id, 'like_id': id + '%', 'status': status, 'change': history}, returning=True)

    def tag_alert(self, id, tags):
        update = """
            UPDATE alerts
            SET tags=ARRAY(SELECT DISTINCT UNNEST(tags || %(tags)s))
            WHERE id=%(id)s OR id LIKE %(like_id)s
            RETURNING *
        """
        return self._update(update, {'id': id, 'like_id': id + '%', 'tags': tags}, returning=True)

    def untag_alert(self, id, tags):
        update = """
            UPDATE alerts
            SET tags=(select array_agg(t) FROM unnest(tags) AS t WHERE NOT t=ANY(%(tags)s) )
            WHERE id=%(id)s OR id LIKE %(like_id)s
            RETURNING *
        """
        return self._update(update, {'id': id, 'like_id': id+'%', 'tags': tags}, returning=True)

    def update_attributes(self, id, old_attrs, new_attrs):
        old_attrs.update(new_attrs)
        attrs = dict([k, v] for k, v in old_attrs.items() if v is not None)
        update = """
            UPDATE alerts
            SET attributes=%(attrs)s
            WHERE id=%(id)s OR id LIKE %(like_id)s
            RETURNING *
        """
        return self._update(update, {'id': id, 'like_id': id+'%', 'attrs': attrs}, returning=True)

    def delete_alert(self, id):
        delete = """
            DELETE FROM alerts
            WHERE id=%(id)s OR id LIKE %(like_id)s
            RETURNING id
        """
        return self._delete(delete, {'id': id, 'like_id': id+'%'}, returning=True)

    #### SEARCH & HISTORY

    def get_alerts(self, query=None, page=None, page_size=None):
        query = query or Query()
        select = """
            SELECT * FROM alerts
            WHERE {where}
            ORDER BY {order}
        """.format(where=query.where, order=query.sort or 'last_receive_time')
        return self._fetchall(select, query.vars, limit=page_size, offset=(page - 1) * page_size)

    def get_history(self, query=None, page=None, page_size=None):
        query = query or Query()
        select = """
            SELECT resource, environment, service, "group", tags, attributes, origin, customer,
                   history, h.* from alerts, unnest(history) h
             WHERE {where}
        """.format(where=query.where)
        Record = namedtuple("Record", ['id', 'resource', 'event', 'environment', 'severity', 'status', 'service',
                                       'group', 'value', 'text', 'tags', 'attributes', 'origin', 'update_time',
                                       'type', 'customer'])
        return [
            Record(
                id=h.id,
                resource=h.resource,
                event=h.event,
                environment=h.environment,
                severity=h.severity,
                status=h.status,
                service=h.service,
                group=h.group,
                value=h.value,
                text=h.text,
                tags=h.tags,
                attributes=h.attributes,
                origin=h.origin,
                update_time=h.update_time,
                type=h.type,
                customer=h.customer
            ) for h in self._fetchall(select, query.vars, limit=page_size, offset=(page - 1) * page_size)
        ]

    #### COUNTS

    def get_count(self, query=None):
        query = query or Query()
        select = """
            SELECT COUNT(1) FROM alerts
             WHERE {where}
        """.format(where=query.where)
        return self._fetchone(select, query.vars).count

    def get_counts(self, query=None, group=None):
        query = query or Query()
        if group is None:
            raise ValueError('Must define a group')
        select = """
            SELECT {group}, COUNT(*) FROM alerts
             WHERE {where}
            GROUP BY {group}
        """.format(where=query.where, group=group)
        return dict([(s['group'], s.count) for s in self._fetchall(select, query.vars)])

    def get_counts_by_severity(self, query=None):
        query = query or Query()
        select = """
            SELECT severity, COUNT(*) FROM alerts
             WHERE {where}
            GROUP BY severity
        """.format(where=query.where)
        return dict([(s.severity, s.count) for s in self._fetchall(select, query.vars)])

    def get_counts_by_status(self, query=None):
        query = query or Query()
        select = """
            SELECT status, COUNT(*) FROM alerts
            WHERE {where}
            GROUP BY status
        """.format(where=query.where)
        return dict([(s.status, s.count) for s in self._fetchall(select, query.vars)])

    def get_topn_count(self, query=None, group="event", topn=10):
        query = query or Query()
        select = """
            SELECT event, COUNT(1) as count, SUM(duplicate_count) AS duplicate_count,
                   array_agg(DISTINCT environment) AS environments, array_agg(DISTINCT svc) AS services,
                   array_agg(DISTINCT ARRAY[id, resource]) AS resources
              FROM alerts, UNNEST (service) svc
             WHERE {where}
          GROUP BY event
          ORDER BY count DESC
        """.format(where=query.where)
        return [
            {
                "count": t.count,
                "duplicateCount": t.duplicate_count,
                "environments": t.environments,
                "event": t.event,
                "resources": [{"id": r[0], "resource": r[1], "href": absolute_url('/alert/%s' % r[0])} for r in t.resources]
            } for t in self._fetchall(select, query.vars, limit=topn)
        ]

    def get_topn_flapping(self, query=None, group="event", topn=10):
        query = query or Query()
        select = """
            SELECT alerts.event, COUNT(1) as count, SUM(duplicate_count) AS duplicate_count,
                   array_agg(DISTINCT environment) AS environments, array_agg(DISTINCT svc) AS services,
                   array_agg(DISTINCT ARRAY[alerts.id, resource]) AS resources
              FROM alerts, UNNEST (service) svc, UNNEST (history) hist
             WHERE hist.type='severity' AND {where}
          GROUP BY alerts.event
          ORDER BY count DESC
        """.format(where=query.where)
        return [
            {
                "count": t.count,
                "duplicateCount": t.duplicate_count,
                "environments": t.environments,
                "event": t.event,
                "resources": [{"id": r[0], "resource": r[1], "href": absolute_url('/alert/%s' % r[0])} for r in t.resources]
            } for t in self._fetchall(select, query.vars, limit=topn)
        ]

    #### ENVIRONMENTS

    def get_environments(self, query=None, topn=100):
        query = query or Query()
        select = """
            SELECT environment, count(1) FROM alerts
            WHERE {where}
            GROUP BY environment
        """.format(where=query.where)
        return [{"environment": e.environment, "count": e.count} for e in self._fetchall(select, query.vars, limit=topn)]

    #### SERVICES

    def get_services(self, query=None, topn=100):
        query = query or Query()
        select = """
            SELECT environment, svc, count(1) FROM alerts, UNNEST(service) svc
            WHERE {where}
            GROUP BY environment, svc
        """.format(where=query.where)
        return [{"environment": s.environment, "service": s.svc, "count": s.count} for s in self._fetchall(select, query.vars, limit=topn)]

    #### SERVICES

    def get_tags(self, query=None, topn=100):
        query = query or Query()
        select = """
            SELECT environment, tag, count(1) FROM alerts, UNNEST(tags) tag
            WHERE {where}
            GROUP BY environment, tag
        """.format(where=query.where)
        return [{"environment": t.environment, "tag": t.tag, "count": t.count} for t in self._fetchall(select, query.vars, limit=topn)]

    #### BLACKOUTS

    def create_blackout(self, blackout):
        insert = """
            INSERT INTO blackouts (id, priority, environment, service, resource, event, "group", tags, customer, start_time, end_time, duration)
            VALUES (%(id)s, %(priority)s, %(environment)s, %(service)s, %(resource)s, %(event)s, %(group)s, %(tags)s, %(customer)s, %(start_time)s, %(end_time)s, %(duration)s)
            RETURNING *
        """
        return self._insert(insert, vars(blackout))

    def get_blackout(self, id, customer=None):
        select = """
            SELECT * FROM blackouts
            WHERE id=%(id)s
              AND customer IS NOT DISTINCT FROM %(customer)s
        """
        return self._fetchone(select, {'id': id, 'customer': customer})

    def get_blackouts(self, query=None):
        query = query or Query()
        select = """
            SELECT * FROM blackouts
            WHERE {where}
        """.format(where=query.where)
        return self._fetchall(select, query.vars)

    def is_blackout_period(self, alert):
        now = datetime.utcnow()
        select = """
            SELECT *
            FROM blackouts
            WHERE start_time <= %(now)s AND end_time > %(now)s
              AND environment=%(environment)s
              AND (
                 (resource IS NULL AND service='{}' AND event IS NULL AND "group" IS NULL AND tags='{}')
              OR (resource=%(resource)s AND service='{}' AND event IS NULL AND "group" IS NULL AND tags='{}') 
              OR (resource IS NULL AND service::text[] && %(service)s AND event IS NULL AND "group" IS NULL AND tags='{}')
              OR (resource IS NULL AND service='{}' AND event=%(event)s AND "group" IS NULL AND tags='{}')
              OR (resource IS NULL AND service='{}' AND event IS NULL AND "group"=%(group)s AND tags='{}')
              OR (resource=%(resource)s AND service='{}' AND event=%(event)s AND "group" IS NULL AND tags='{}')
              OR (resource IS NULL AND service='{}' AND event IS NULL AND "group" IS NULL AND tags <@ %(tags)s)
                )
        """
        data = vars(alert)
        data['now'] = now
        if self._fetchone(select, data):
            return True
        if current_app.config['CUSTOMER_VIEWS']:
            select += " AND customer IS NOT DISTINCT FROM %(customer)s"
            if self._fetchone(select, data):
                return True
        return False

    def delete_blackout(self, id):
        delete = """
            DELETE FROM blackouts
            WHERE id=%s
            RETURNING id
        """
        return self._delete(delete, (id,), returning=True)

    #### HEARTBEATS

    def upsert_heartbeat(self, heartbeat):
        upsert = """
            INSERT INTO heartbeats (id, origin, tags, type, create_time, timeout, receive_time, customer)
            VALUES (%(id)s, %(origin)s, %(tags)s, %(event_type)s, %(create_time)s, %(timeout)s, %(receive_time)s, %(customer)s)
            ON CONFLICT (origin, COALESCE(customer, '')) DO UPDATE
                SET tags=%(tags)s, create_time=%(create_time)s, timeout=%(timeout)s, receive_time=%(receive_time)s
            RETURNING *
        """
        return self._upsert(upsert, vars(heartbeat))

    def get_heartbeat(self, id, customer=None):
        select = """
            SELECT * FROM heartbeats
             WHERE id=%(id)s OR id LIKE %(like_id)s
               AND customer IS NOT DISTINCT FROM %(customer)s
        """
        return self._fetchone(select, {'id': id, 'like_id': id+'%', 'customer': customer})

    def get_heartbeats(self, query=None):
        query = query or Query()
        select = """
            SELECT * FROM heartbeats
            WHERE {where}    
        """.format(where=query.where)
        return self._fetchall(select, query.vars)

    def delete_heartbeat(self, id):
        delete = """
            DELETE FROM heartbeats
            WHERE id=%(id)s OR id LIKE %(like_id)s
            RETURNING id
        """
        return self._delete(delete, {'id': id, 'like_id': id+'%'}, returning=True)

    #### API KEYS

    def create_key(self, key):
        insert = """
            INSERT INTO keys (id, key, "user", scopes, text, expire_time, "count", last_used_time, customer)
            VALUES (%(id)s, %(key)s, %(user)s, %(scopes)s, %(text)s, %(expire_time)s, %(count)s, %(last_used_time)s, %(customer)s)
            RETURNING *
        """
        return self._insert(insert, vars(key))

    def get_key(self, key):
        select = """
            SELECT * FROM keys
             WHERE id=%s OR key=%s
        """
        return self._fetchone(select, (key, key))

    def get_keys(self, query=None):
        query = query or Query()
        select = """
            SELECT * FROM keys
            WHERE {where}
        """.format(where=query.where)
        return self._fetchall(select, query.vars)

    def update_key_last_used(self, key):
        update = """
            UPDATE keys
            SET last_used_time=%s, count=count+1
            WHERE id=%s OR key=%s
        """
        return self._update(update, (datetime.utcnow(), key, key))

    def delete_key(self, key):
        delete = """
            DELETE FROM keys
            WHERE id=%s OR key=%s
            RETURNING key
        """
        return self._delete(delete, (key, key), returning=True)

    #### USERS

    def create_user(self, user):
        insert = """
            INSERT INTO users (id, name, email, password, status, roles, attributes,
                create_time, last_login, text, update_time, email_verified)
            VALUES (%(id)s, %(name)s, %(email)s, %(password)s, %(status)s, %(roles)s, %(attributes)s, %(create_time)s,
                %(last_login)s, %(text)s, %(update_time)s, %(email_verified)s)
            RETURNING *
        """
        return self._insert(insert, vars(user))

    def get_user(self, id):
        select = """SELECT * FROM users WHERE id=%s"""
        return self._fetchone(select, (id,))

    def get_users(self, query=None):
        query = query or Query()
        select = """
            SELECT * FROM users
            WHERE {where}
        """.format(where=query.where)
        return self._fetchall(select, query.vars)

    def get_user_by_email(self, email):
        select = """SELECT * FROM users WHERE email=%s"""
        return self._fetchone(select, (email,))

    def get_user_by_hash(self, hash):
        select = """SELECT * FROM users WHERE hash=%s"""
        return self._fetchone(select, (hash,))

    def update_last_login(self, id):
        update = """
            UPDATE users
            SET last_login=%s
            WHERE id=%s
        """
        return self._update(update, (datetime.utcnow(), id))

    def set_email_hash(self, id, hash):
        update = """
            UPDATE users
            SET hash=%s
            WHERE id=%s
        """
        return self._update(update, (hash, id))

    def update_user(self, id, **kwargs):
        kwargs['update_time'] = datetime.utcnow()
        update = """
            UPDATE users
            SET
        """
        if 'name' in kwargs:
            update += "name=%(name)s, "
        if 'email' in kwargs:
            update += "email=%(email)s, "
        if 'password' in kwargs:
            update += "password=%(password)s, "
        if 'status' in kwargs:
            update += "status=%(status)s, "
        if 'roles' in kwargs:
            update += "roles=%(roles)s, "
        if 'attributes' in kwargs:
            update += "attributes=attributes || %(attributes)s, "
        if 'text' in kwargs:
            update += "text=%(text)s, "
        if 'email_verified' in kwargs:
            update += "email_verified=%(email_verified)s, "
        update += """
            update_time=%(update_time)s
            WHERE id=%(id)s
            RETURNING *
        """
        kwargs['id'] = id
        return self._update(update, kwargs, returning=True)

    def update_user_attributes(self, id, old_attrs, new_attrs):
        old_attrs.update(new_attrs)
        attrs = dict([k, v] for k, v in old_attrs.items() if v is not None)
        update = """
            UPDATE users
               SET attributes=%(attrs)s
             WHERE id=%(id)s
            RETURNING *
        """
        return self._update(update, {'id': id, 'attrs': attrs}, returning=True)

    def delete_user(self, id):
        delete = """
            DELETE FROM users
            WHERE id=%s
            RETURNING id
        """
        return self._delete(delete, (id,), returning=True)

    #### PERMISSIONS

    def create_perm(self, perm):
        insert = """
            INSERT INTO perms (id, match, scopes)
            VALUES (%(id)s, %(match)s, %(scopes)s)
            RETURNING *
        """
        return self._insert(insert, vars(perm))

    def get_perm(self, id):
        select = """SELECT * FROM perms WHERE id=%s"""
        return self._fetchone(select, (id,))

    def get_perms(self, query=None):
        query = query or Query()
        select = """
            SELECT * FROM perms
            WHERE {where}
        """.format(where=query.where)
        return self._fetchall(select, query.vars)

    def delete_perm(self, id):
        delete = """
            DELETE FROM perms
            WHERE id=%s
            RETURNING id
        """
        return self._delete(delete, (id,), returning=True)

    def get_scopes_by_match(self, login, matches):
        if login in current_app.config['ADMIN_USERS']:
            return ['admin', 'read', 'write']

        scopes = list()
        for match in matches:
            select = """SELECT scopes FROM perms WHERE match=%s"""
            response = self._fetchone(select, (match,))
            if response:
                scopes.extend(response.scopes)
        return set(scopes) or current_app.config['USER_DEFAULT_SCOPES']

    #### CUSTOMERS

    def create_customer(self, customer):
        insert = """
            INSERT INTO customers (id, match, customer)
            VALUES (%(id)s, %(match)s, %(customer)s)
            RETURNING *
        """
        return self._insert(insert, vars(customer))

    def get_customer(self, id):
        select = """SELECT * FROM customers WHERE id=%s"""
        return self._fetchone(select, (id,))

    def get_customers(self, query=None):
        query = query or Query()
        select = """
            SELECT * FROM customers
            WHERE {where}
        """.format(where=query.where)
        return self._fetchall(select, query.vars)

    def delete_customer(self, id):
        delete = """
            DELETE FROM customers
            WHERE id=%s
            RETURNING id
        """
        return self._delete(delete, (id,), returning=True)

    def get_customers_by_match(self, login, matches):
        if login in current_app.config['ADMIN_USERS']:
            return '*'  # all customers

        for match in [login] + matches:
            select = """SELECT customer FROM customers WHERE match=%s"""
            response = self._fetchone(select, (match,))
            if response:
                return response.customer
        raise NoCustomerMatch("No customer lookup configured for user '%s' or '%s'" % (login, ','.join(matches)))

    #### METRICS

    def get_metrics(self, type=None):
        select = """SELECT * FROM metrics"""
        if type:
            select += " WHERE type=%s"
        return self._fetchall(select, (type,))

    def set_gauge(self, gauge):
        upsert = """
            INSERT INTO metrics ("group", name, title, description, value, type)
            VALUES (%(group)s, %(name)s, %(title)s, %(description)s, %(value)s, %(type)s)
            ON CONFLICT ("group", name, type) DO UPDATE
                SET value=%(value)s
            RETURNING *
        """
        return self._upsert(upsert, vars(gauge))

    def inc_counter(self, counter):
        upsert = """
            INSERT INTO metrics ("group", name, title, description, count, type)
            VALUES (%(group)s, %(name)s, %(title)s, %(description)s, %(count)s, %(type)s)
            ON CONFLICT ("group", name, type) DO UPDATE
                SET count=metrics.count+%(count)s
            RETURNING *
        """
        return self._upsert(upsert, vars(counter))

    def update_timer(self, timer):
        upsert = """
            INSERT INTO metrics ("group", name, title, description, count, total_time, type)
            VALUES (%(group)s, %(name)s, %(title)s, %(description)s, %(count)s, %(total_time)s, %(type)s)
            ON CONFLICT ("group", name, type) DO UPDATE
                SET count=metrics.count+%(count)s, total_time=metrics.total_time+%(total_time)s
            RETURNING *
        """
        return self._upsert(upsert, vars(timer))

    #### HOUSEKEEPING

    def housekeeping(self, expired_threshold, info_threshold):
        # delete 'closed' or 'expired' alerts older than "expired_threshold" hours
        # and 'informational' alerts older than "info_threshold" hours
        delete = """
            DELETE FROM alerts
             WHERE (status IN ('closed', 'expired')
                    AND last_receive_time < (NOW() at time zone 'utc' - INTERVAL '%(expired_threshold)s hours'))
                OR (severity='informational'
                    AND last_receive_time < (NOW() at time zone 'utc' - INTERVAL '%(info_threshold)s hours'))
        """
        self._delete(delete, {"expired_threshold": expired_threshold, "info_threshold": info_threshold})

        # return list of alerts to be newly expired
        update = """
            SELECT id, event, last_receive_id
              FROM alerts
             WHERE status!='expired' AND timeout!=0
               AND (last_receive_time + INTERVAL '1 second' * timeout) < (NOW() at time zone 'utc')
        """
        return self._fetchall(update, {})

    #### SQL HELPERS

    def _insert(self, query, vars):
        """
        Insert, with return.
        """
        cursor = g.db.cursor()
        self._log(cursor, query, vars)
        cursor.execute(query, vars)
        g.db.commit()
        return cursor.fetchone()

    def _fetchone(self, query, vars):
        """
        Return none or one row.
        """
        cursor = g.db.cursor()
        self._log(cursor, query, vars)
        cursor.execute(query, vars)
        return cursor.fetchone()

    def _fetchall(self, query, vars, limit=None, offset=0):
        """
        Return multiple rows.
        """
        if limit is None:
            limit = current_app.config['DEFAULT_PAGE_SIZE']
        query += " LIMIT %s OFFSET %s""" % (limit, offset)
        cursor = g.db.cursor()
        self._log(cursor, query, vars)
        cursor.execute(query, vars)
        return cursor.fetchall()

    def _update(self, query, vars, returning=False):
        """
        Update, with optional return.
        """
        cursor = g.db.cursor()
        self._log(cursor, query, vars)
        cursor.execute(query, vars)
        g.db.commit()
        return cursor.fetchone() if returning else None

    def _upsert(self, query, vars):
        """
        Insert or update, with return.
        """
        return self._insert(query, vars)

    def _delete(self, query, vars, returning=False):
        """
        Delete, with optional return.
        """
        cursor = g.db.cursor()
        self._log(cursor, query, vars)
        cursor.execute(query, vars)
        g.db.commit()
        return cursor.fetchone() if returning else None

    def _log(self, cursor, query, vars):
        LOG = current_app.logger
        LOG.debug(cursor.mogrify(query, vars))
