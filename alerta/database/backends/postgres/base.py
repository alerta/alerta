import time
from collections import defaultdict, namedtuple
from datetime import datetime

import psycopg2
from flask import current_app
from psycopg2.extensions import AsIs, adapt, register_adapter
from psycopg2.extras import Json, NamedTupleCursor, register_composite

from alerta.app import alarm_model
from alerta.database.base import Database
from alerta.exceptions import NoCustomerMatch
from alerta.models.enums import ADMIN_SCOPES
from alerta.utils.format import DateTime
from alerta.utils.response import absolute_url

from .utils import Query

MAX_RETRIES = 5


class HistoryAdapter:
    def __init__(self, history):
        self.history = history
        self.conn = None

    def prepare(self, conn):
        self.conn = conn

    def getquoted(self):
        def quoted(o):
            a = adapt(o)
            if hasattr(a, 'prepare'):
                a.prepare(self.conn)
            return a.getquoted().decode('utf-8')

        return '({}, {}, {}, {}, {}, {}, {}, {}::timestamp, {}, {})::history'.format(
            quoted(self.history.id),
            quoted(self.history.event),
            quoted(self.history.severity),
            quoted(self.history.status),
            quoted(self.history.value),
            quoted(self.history.text),
            quoted(self.history.change_type),
            quoted(self.history.update_time),
            quoted(self.history.user),
            quoted(self.history.timeout)
        )

    def __str__(self):
        return str(self.getquoted())


Record = namedtuple('Record', [
    'id', 'resource', 'event', 'environment', 'severity', 'status', 'service',
    'group', 'value', 'text', 'tags', 'attributes', 'origin', 'update_time',
    'user', 'timeout', 'type', 'customer'
])


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
        register_adapter(History, HistoryAdapter)

    def connect(self):
        retry = 0
        while True:
            try:
                conn = psycopg2.connect(
                    dsn=self.uri,
                    dbname=self.dbname,
                    cursor_factory=NamedTupleCursor
                )
                conn.set_client_encoding('UTF8')
                break
            except Exception as e:
                print(e)  # FIXME - should log this error instead of printing, but current_app is unavailable here
                retry += 1
                if retry > MAX_RETRIES:
                    conn = None
                    break
                else:
                    backoff = 2 ** retry
                    print('Retry attempt {}/{} (wait={}s)...'.format(retry, MAX_RETRIES, backoff))
                    time.sleep(backoff)

        if conn:
            return conn
        else:
            raise RuntimeError('Database connect error. Failed to connect after {} retries.'.format(MAX_RETRIES))

    @staticmethod
    def _adapt_datetime(dt):
        return AsIs('%s' % adapt(DateTime.iso8601(dt)))

    @property
    def name(self):
        cursor = self.get_db().cursor()
        cursor.execute('SELECT current_database()')
        return cursor.fetchone()[0]

    @property
    def version(self):
        cursor = self.get_db().cursor()
        cursor.execute('SHOW server_version')
        return cursor.fetchone()[0]

    @property
    def is_alive(self):
        cursor = self.get_db().cursor()
        cursor.execute('SELECT true')
        return cursor.fetchone()

    def close(self, db):
        db.close()

    def destroy(self):
        conn = self.connect()
        cursor = conn.cursor()
        for table in ['alerts', 'blackouts', 'customers', 'groups', 'heartbeats', 'keys', 'metrics', 'perms', 'users']:
            cursor.execute('DROP TABLE IF EXISTS %s' % table)
        conn.commit()
        conn.close()

    # ALERTS

    def get_severity(self, alert):
        select = """
            SELECT severity FROM alerts
             WHERE environment=%(environment)s AND resource=%(resource)s
               AND ((event=%(event)s AND severity!=%(severity)s)
                OR (event!=%(event)s AND %(event)s=ANY(correlate)))
               AND {customer}
            """.format(customer='customer=%(customer)s' if alert.customer else 'customer IS NULL')
        return self._fetchone(select, vars(alert)).severity

    def get_status(self, alert):
        select = """
            SELECT status FROM alerts
             WHERE environment=%(environment)s AND resource=%(resource)s
              AND (event=%(event)s OR %(event)s=ANY(correlate))
              AND {customer}
            """.format(customer='customer=%(customer)s' if alert.customer else 'customer IS NULL')
        return self._fetchone(select, vars(alert)).status

    def is_duplicate(self, alert):
        select = """
            SELECT * FROM alerts
             WHERE environment=%(environment)s
               AND resource=%(resource)s
               AND event=%(event)s
               AND severity=%(severity)s
               AND {customer}
            """.format(customer='customer=%(customer)s' if alert.customer else 'customer IS NULL')
        return self._fetchone(select, vars(alert))

    def is_correlated(self, alert):
        select = """
            SELECT * FROM alerts
             WHERE environment=%(environment)s AND resource=%(resource)s
               AND ((event=%(event)s AND severity!=%(severity)s)
                OR (event!=%(event)s AND %(event)s=ANY(correlate)))
               AND {customer}
        """.format(customer='customer=%(customer)s' if alert.customer else 'customer IS NULL')
        return self._fetchone(select, vars(alert))

    def is_flapping(self, alert, window=1800, count=2):
        """
        Return true if alert severity has changed more than X times in Y seconds
        """
        select = """
            SELECT COUNT(*)
              FROM alerts, unnest(history) h
             WHERE environment=%(environment)s
               AND resource=%(resource)s
               AND h.event=%(event)s
               AND h.update_time > (NOW() at time zone 'utc' - INTERVAL '{window} seconds')
               AND h.type='severity'
               AND {customer}
        """.format(window=window, customer='customer=%(customer)s' if alert.customer else 'customer IS NULL')
        return self._fetchone(select, vars(alert)).count > count

    def dedup_alert(self, alert, history):
        """
        Update alert status, service, value, text, timeout and rawData, increment duplicate count and set
        repeat=True, and keep track of last receive id and time but don't append to history unless status changes.
        """
        alert.history = history
        update = """
            UPDATE alerts
               SET status=%(status)s, service=%(service)s, value=%(value)s, text=%(text)s,
                   timeout=%(timeout)s, raw_data=%(raw_data)s, repeat=%(repeat)s,
                   last_receive_id=%(last_receive_id)s, last_receive_time=%(last_receive_time)s,
                   tags=ARRAY(SELECT DISTINCT UNNEST(tags || %(tags)s)), attributes=attributes || %(attributes)s,
                   duplicate_count=duplicate_count + 1, {update_time}, history=(%(history)s || history)[1:{limit}]
             WHERE environment=%(environment)s
               AND resource=%(resource)s
               AND event=%(event)s
               AND severity=%(severity)s
               AND {customer}
         RETURNING *
        """.format(
            limit=current_app.config['HISTORY_LIMIT'],
            update_time='update_time=%(update_time)s' if alert.update_time else 'update_time=update_time',
            customer='customer=%(customer)s' if alert.customer else 'customer IS NULL'
        )
        return self._updateone(update, vars(alert), returning=True)

    def correlate_alert(self, alert, history):
        alert.history = history
        update = """
            UPDATE alerts
               SET event=%(event)s, severity=%(severity)s, status=%(status)s, service=%(service)s, value=%(value)s,
                   text=%(text)s, create_time=%(create_time)s, timeout=%(timeout)s, raw_data=%(raw_data)s,
                   duplicate_count=%(duplicate_count)s, repeat=%(repeat)s, previous_severity=%(previous_severity)s,
                   trend_indication=%(trend_indication)s, receive_time=%(receive_time)s, last_receive_id=%(last_receive_id)s,
                   last_receive_time=%(last_receive_time)s, tags=ARRAY(SELECT DISTINCT UNNEST(tags || %(tags)s)),
                   attributes=attributes || %(attributes)s, {update_time}, history=(%(history)s || history)[1:{limit}]
             WHERE environment=%(environment)s
               AND resource=%(resource)s
               AND ((event=%(event)s AND severity!=%(severity)s) OR (event!=%(event)s AND %(event)s=ANY(correlate)))
               AND {customer}
         RETURNING *
        """.format(
            limit=current_app.config['HISTORY_LIMIT'],
            update_time='update_time=%(update_time)s' if alert.update_time else 'update_time=update_time',
            customer='customer=%(customer)s' if alert.customer else 'customer IS NULL'
        )
        return self._updateone(update, vars(alert), returning=True)

    def create_alert(self, alert):
        insert = """
            INSERT INTO alerts (id, resource, event, environment, severity, correlate, status, service, "group",
                value, text, tags, attributes, origin, type, create_time, timeout, raw_data, customer,
                duplicate_count, repeat, previous_severity, trend_indication, receive_time, last_receive_id,
                last_receive_time, update_time, history)
            VALUES (%(id)s, %(resource)s, %(event)s, %(environment)s, %(severity)s, %(correlate)s, %(status)s,
                %(service)s, %(group)s, %(value)s, %(text)s, %(tags)s, %(attributes)s, %(origin)s,
                %(event_type)s, %(create_time)s, %(timeout)s, %(raw_data)s, %(customer)s, %(duplicate_count)s,
                %(repeat)s, %(previous_severity)s, %(trend_indication)s, %(receive_time)s, %(last_receive_id)s,
                %(last_receive_time)s, %(update_time)s, %(history)s::history[])
            RETURNING *
        """
        return self._insert(insert, vars(alert))

    def set_alert(self, id, severity, status, tags, attributes, timeout, previous_severity, update_time, history=None):
        update = """
            UPDATE alerts
               SET severity=%(severity)s, status=%(status)s, tags=ARRAY(SELECT DISTINCT UNNEST(tags || %(tags)s)),
                   attributes=%(attributes)s, timeout=%(timeout)s, previous_severity=%(previous_severity)s,
                   update_time=%(update_time)s, history=(%(change)s || history)[1:{limit}]
             WHERE id=%(id)s OR id LIKE %(like_id)s
         RETURNING *
        """.format(limit=current_app.config['HISTORY_LIMIT'])
        return self._updateone(update, {'id': id, 'like_id': id + '%', 'severity': severity, 'status': status,
                                        'tags': tags, 'attributes': attributes, 'timeout': timeout,
                                        'previous_severity': previous_severity, 'update_time': update_time,
                                        'change': history}, returning=True)

    def get_alert(self, id, customers=None):
        select = """
            SELECT * FROM alerts
             WHERE (id ~* (%(id)s) OR last_receive_id ~* (%(id)s))
               AND {customer}
        """.format(customer='customer=ANY(%(customers)s)' if customers else '1=1')
        return self._fetchone(select, {'id': '^' + id, 'customers': customers})

    # STATUS, TAGS, ATTRIBUTES

    def set_status(self, id, status, timeout, update_time, history=None):
        update = """
            UPDATE alerts
            SET status=%(status)s, timeout=%(timeout)s, update_time=%(update_time)s, history=(%(change)s || history)[1:{limit}]
            WHERE id=%(id)s OR id LIKE %(like_id)s
            RETURNING *
        """.format(limit=current_app.config['HISTORY_LIMIT'])
        return self._updateone(update, {'id': id, 'like_id': id + '%', 'status': status, 'timeout': timeout, 'update_time': update_time, 'change': history}, returning=True)

    def tag_alert(self, id, tags):
        update = """
            UPDATE alerts
            SET tags=ARRAY(SELECT DISTINCT UNNEST(tags || %(tags)s))
            WHERE id=%(id)s OR id LIKE %(like_id)s
            RETURNING *
        """
        return self._updateone(update, {'id': id, 'like_id': id + '%', 'tags': tags}, returning=True)

    def untag_alert(self, id, tags):
        update = """
            UPDATE alerts
            SET tags=(select array_agg(t) FROM unnest(tags) AS t WHERE NOT t=ANY(%(tags)s) )
            WHERE id=%(id)s OR id LIKE %(like_id)s
            RETURNING *
        """
        return self._updateone(update, {'id': id, 'like_id': id + '%', 'tags': tags}, returning=True)

    def update_attributes(self, id, old_attrs, new_attrs):
        old_attrs.update(new_attrs)
        attrs = {k: v for k, v in old_attrs.items() if v is not None}
        update = """
            UPDATE alerts
            SET attributes=%(attrs)s
            WHERE id=%(id)s OR id LIKE %(like_id)s
            RETURNING *
        """
        return self._updateone(update, {'id': id, 'like_id': id + '%', 'attrs': attrs}, returning=True)

    def delete_alert(self, id):
        delete = """
            DELETE FROM alerts
            WHERE id=%(id)s OR id LIKE %(like_id)s
            RETURNING id
        """
        return self._deleteone(delete, {'id': id, 'like_id': id + '%'}, returning=True)

    # BULK

    def tag_alerts(self, query=None, tags=None):
        query = query or Query()
        update = """
            UPDATE alerts
            SET tags=ARRAY(SELECT DISTINCT UNNEST(tags || %(_tags)s))
            WHERE {where}
            RETURNING id
        """.format(where=query.where)
        return [row[0] for row in self._updateall(update, {**query.vars, **{'_tags': tags}}, returning=True)]

    def untag_alerts(self, query=None, tags=None):
        query = query or Query()
        update = """
            UPDATE alerts
            SET tags=(select array_agg(t) FROM unnest(tags) AS t WHERE NOT t=ANY(%(_tags)s) )
            WHERE {where}
            RETURNING id
        """.format(where=query.where)
        return [row[0] for row in self._updateall(update, {**query.vars, **{'_tags': tags}}, returning=True)]

    def update_attributes_by_query(self, query=None, attributes=None):
        update = """
            UPDATE alerts
            SET attributes=attributes || %(_attributes)s
            WHERE {where}
            RETURNING id
        """.format(where=query.where)
        return [row[0] for row in self._updateall(update, {**query.vars, **{'_attributes': attributes}}, returning=True)]

    def delete_alerts(self, query=None):
        query = query or Query()
        delete = """
            DELETE FROM alerts
            WHERE {where}
            RETURNING id
        """.format(where=query.where)
        return [row[0] for row in self._deleteall(delete, query.vars, returning=True)]

    # SEARCH & HISTORY

    def add_history(self, id, history):
        update = """
            UPDATE alerts
               SET history=(%(history)s || history)[1:{limit}]
             WHERE id=%(id)s OR id LIKE %(like_id)s
         RETURNING *
        """.format(limit=current_app.config['HISTORY_LIMIT'])
        return self._updateone(update, {'id': id, 'like_id': id + '%', 'history': history}, returning=True)

    def get_alerts(self, query=None, page=None, page_size=None):
        query = query or Query()
        join = ''
        if 's.code' in query.sort:
            join += 'JOIN (VALUES {}) AS s(sev, code) ON alerts.severity = s.sev '.format(
                ', '.join(("('{}', {})".format(k, v) for k, v in alarm_model.Severity.items()))
            )
        if 'st.state' in query.sort:
            join += 'JOIN (VALUES {}) AS st(sts, state) ON alerts.status = st.sts '.format(
                ', '.join(("('{}', '{}')".format(k, v) for k, v in alarm_model.Status.items()))
            )
        select = """
            SELECT *
              FROM alerts {join}
             WHERE {where}
          ORDER BY {order}
        """.format(join=join, where=query.where, order=query.sort or 'last_receive_time')
        return self._fetchall(select, query.vars, limit=page_size, offset=(page - 1) * page_size)

    def get_alert_history(self, alert, page=None, page_size=None):
        select = """
            SELECT resource, environment, service, "group", tags, attributes, origin, customer, h.*
              FROM alerts, unnest(history[1:{limit}]) h
             WHERE environment=%(environment)s AND resource=%(resource)s
               AND (h.event=%(event)s OR %(event)s=ANY(correlate))
               AND {customer}
          ORDER BY update_time DESC
            """.format(
            customer='customer=%(customer)s' if alert.customer else 'customer IS NULL',
            limit=current_app.config['HISTORY_LIMIT']
        )
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
                user=getattr(h, 'user', None),
                timeout=getattr(h, 'timeout', None),
                type=h.type,
                customer=h.customer
            ) for h in self._fetchall(select, vars(alert), limit=page_size, offset=(page - 1) * page_size)
        ]

    def get_history(self, query=None, page=None, page_size=None):
        query = query or Query()
        if 'id' in query.vars:
            select = """
                SELECT a.id
                  FROM alerts a, unnest(history[1:{limit}]) h
                 WHERE h.id LIKE %(id)s
            """.format(limit=current_app.config['HISTORY_LIMIT'])
            query.vars['id'] = self._fetchone(select, query.vars)

        select = """
            SELECT resource, environment, service, "group", tags, attributes, origin, customer, history, h.*
              FROM alerts, unnest(history[1:{limit}]) h
             WHERE {where}
          ORDER BY update_time DESC
        """.format(where=query.where, limit=current_app.config['HISTORY_LIMIT'])

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
                user=getattr(h, 'user', None),
                timeout=getattr(h, 'timeout', None),
                type=h.type,
                customer=h.customer
            ) for h in self._fetchall(select, query.vars, limit=page_size, offset=(page - 1) * page_size)
        ]

    # COUNTS

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
        return {s['group']: s.count for s in self._fetchall(select, query.vars)}

    def get_counts_by_severity(self, query=None):
        query = query or Query()
        select = """
            SELECT severity, COUNT(*) FROM alerts
             WHERE {where}
            GROUP BY severity
        """.format(where=query.where)
        return {s.severity: s.count for s in self._fetchall(select, query.vars)}

    def get_counts_by_status(self, query=None):
        query = query or Query()
        select = """
            SELECT status, COUNT(*) FROM alerts
            WHERE {where}
            GROUP BY status
        """.format(where=query.where)
        return {s.status: s.count for s in self._fetchall(select, query.vars)}

    def get_topn_count(self, query=None, group='event', topn=100):
        query = query or Query()
        select = """
            SELECT event, COUNT(1) as count, SUM(duplicate_count) AS duplicate_count,
                   array_agg(DISTINCT environment) AS environments, array_agg(DISTINCT svc) AS services,
                   array_agg(DISTINCT ARRAY[id, resource]) AS resources
              FROM alerts, UNNEST (service) svc
             WHERE {where}
          GROUP BY {group}
          ORDER BY count DESC
        """.format(where=query.where, group=group)
        return [
            {
                'count': t.count,
                'duplicateCount': t.duplicate_count,
                'environments': t.environments,
                'services': t.services,
                '%s' % group: t.event,
                'resources': [{'id': r[0], 'resource': r[1], 'href': absolute_url('/alert/%s' % r[0])} for r in t.resources]
            } for t in self._fetchall(select, query.vars, limit=topn)
        ]

    def get_topn_flapping(self, query=None, group='event', topn=100):
        query = query or Query()
        select = """
            WITH topn AS (SELECT * FROM alerts WHERE {where})
            SELECT topn.event, COUNT(1) as count, SUM(duplicate_count) AS duplicate_count,
                   array_agg(DISTINCT environment) AS environments, array_agg(DISTINCT svc) AS services,
                   array_agg(DISTINCT ARRAY[topn.id, resource]) AS resources
              FROM topn, UNNEST (service) svc, UNNEST (history) hist
             WHERE hist.type='severity'
          GROUP BY topn.{group}
          ORDER BY count DESC
        """.format(where=query.where, group=group)
        return [
            {
                'count': t.count,
                'duplicateCount': t.duplicate_count,
                'environments': t.environments,
                'services': t.services,
                'event': t.event,
                'resources': [{'id': r[0], 'resource': r[1], 'href': absolute_url('/alert/%s' % r[0])} for r in t.resources]
            } for t in self._fetchall(select, query.vars, limit=topn)
        ]

    def get_topn_standing(self, query=None, group='event', topn=100):
        query = query or Query()
        select = """
            WITH topn AS (SELECT * FROM alerts WHERE {where})
            SELECT topn.event, COUNT(1) as count, SUM(duplicate_count) AS duplicate_count,
                   SUM(last_receive_time - create_time) as life_time,
                   array_agg(DISTINCT environment) AS environments, array_agg(DISTINCT svc) AS services,
                   array_agg(DISTINCT ARRAY[topn.id, resource]) AS resources
              FROM topn, UNNEST (service) svc, UNNEST (history) hist
             WHERE hist.type='severity'
          GROUP BY topn.{group}
          ORDER BY life_time DESC
        """.format(where=query.where, group=group)
        return [
            {
                'count': t.count,
                'duplicateCount': t.duplicate_count,
                'environments': t.environments,
                'services': t.services,
                'event': t.event,
                'resources': [{'id': r[0], 'resource': r[1], 'href': absolute_url('/alert/%s' % r[0])} for r in t.resources]
            } for t in self._fetchall(select, query.vars, limit=topn)
        ]

    # ENVIRONMENTS

    def get_environments(self, query=None, topn=1000):
        query = query or Query()
        select = """
            SELECT environment, severity, status, count(1) FROM alerts
            WHERE {where}
            GROUP BY environment, CUBE(severity, status)
        """.format(where=query.where)
        result = self._fetchall(select, query.vars, limit=topn)

        severity_count = defaultdict(list)
        status_count = defaultdict(list)
        total_count = defaultdict(int)

        for row in result:
            if row.severity and not row.status:
                severity_count[row.environment].append((row.severity, row.count))
            if not row.severity and row.status:
                status_count[row.environment].append((row.status, row.count))
            if not row.severity and not row.status:
                total_count[row.environment] = row.count

        select = """SELECT DISTINCT environment FROM alerts"""
        environments = self._fetchall(select, {})
        return [
            {
                'environment': e.environment,
                'severityCounts': dict(severity_count[e.environment]),
                'statusCounts': dict(status_count[e.environment]),
                'count': total_count[e.environment]
            } for e in environments]

    # SERVICES

    def get_services(self, query=None, topn=1000):
        query = query or Query()
        select = """
            SELECT environment, svc, severity, status, count(1) FROM alerts, UNNEST(service) svc
            WHERE {where}
            GROUP BY environment, svc, CUBE(severity, status)
        """.format(where=query.where)
        result = self._fetchall(select, query.vars, limit=topn)

        severity_count = defaultdict(list)
        status_count = defaultdict(list)
        total_count = defaultdict(int)

        for row in result:
            if row.severity and not row.status:
                severity_count[(row.environment, row.svc)].append((row.severity, row.count))
            if not row.severity and row.status:
                status_count[(row.environment, row.svc)].append((row.status, row.count))
            if not row.severity and not row.status:
                total_count[(row.environment, row.svc)] = row.count

        select = """SELECT DISTINCT environment, svc FROM alerts, UNNEST(service) svc"""
        services = self._fetchall(select, {})
        return [
            {
                'environment': s.environment,
                'service': s.svc,
                'severityCounts': dict(severity_count[(s.environment, s.svc)]),
                'statusCounts': dict(status_count[(s.environment, s.svc)]),
                'count': total_count[(s.environment, s.svc)]
            } for s in services]

    # ALERT GROUPS

    def get_alert_groups(self, query=None, topn=1000):
        query = query or Query()
        select = """
            SELECT environment, "group", count(1) FROM alerts
            WHERE {where}
            GROUP BY environment, "group"
        """.format(where=query.where)
        return [
            {
                'environment': g.environment,
                'group': g.group,
                'count': g.count
            } for g in self._fetchall(select, query.vars, limit=topn)]

    # ALERT TAGS

    def get_alert_tags(self, query=None, topn=1000):
        query = query or Query()
        select = """
            SELECT environment, tag, count(1) FROM alerts, UNNEST(tags) tag
            WHERE {where}
            GROUP BY environment, tag
        """.format(where=query.where)
        return [{'environment': t.environment, 'tag': t.tag, 'count': t.count} for t in self._fetchall(select, query.vars, limit=topn)]

    # BLACKOUTS

    def create_blackout(self, blackout):
        insert = """
            INSERT INTO blackouts (id, priority, environment, service, resource, event, "group", tags,
                customer, start_time, end_time, duration, "user", create_time, text)
            VALUES (%(id)s, %(priority)s, %(environment)s, %(service)s, %(resource)s, %(event)s, %(group)s, %(tags)s,
                %(customer)s, %(start_time)s, %(end_time)s, %(duration)s, %(user)s, %(create_time)s, %(text)s)
            RETURNING *
        """
        return self._insert(insert, vars(blackout))

    def get_blackout(self, id, customers=None):
        select = """
            SELECT * FROM blackouts
            WHERE id=%(id)s
              AND {customer}
        """.format(customer='customer=ANY(%(customers)s)' if customers else '1=1')
        return self._fetchone(select, {'id': id, 'customers': customers})

    def get_blackouts(self, query=None):
        query = query or Query()
        select = """
            SELECT * FROM blackouts
            WHERE {where}
        """.format(where=query.where)
        return self._fetchall(select, query.vars)

    def is_blackout_period(self, alert):
        select = """
            SELECT *
            FROM blackouts
            WHERE start_time <= %(create_time)s AND end_time > %(create_time)s
              AND environment=%(environment)s
              AND (
                 (resource IS NULL AND service='{}' AND event IS NULL AND "group" IS NULL AND tags='{}')
              OR ( resource IS NULL AND service='{}' AND event IS NULL AND "group" IS NULL AND tags <@ %(tags)s )
              OR ( resource IS NULL AND service='{}' AND event IS NULL AND "group"=%(group)s AND tags='{}' )
              OR ( resource IS NULL AND service='{}' AND event IS NULL AND "group"=%(group)s AND tags <@ %(tags)s )
              OR ( resource IS NULL AND service='{}' AND event=%(event)s AND "group" IS NULL AND tags='{}' )
              OR ( resource IS NULL AND service='{}' AND event=%(event)s AND "group" IS NULL AND tags <@ %(tags)s )
              OR ( resource IS NULL AND service='{}' AND event=%(event)s AND "group"=%(group)s AND tags='{}' )
              OR ( resource IS NULL AND service='{}' AND event=%(event)s AND "group"=%(group)s AND tags <@ %(tags)s )
              OR ( resource IS NULL AND service <@ %(service)s AND event IS NULL AND "group" IS NULL AND tags='{}' )
              OR ( resource IS NULL AND service <@ %(service)s AND event IS NULL AND "group" IS NULL AND tags <@ %(tags)s )
              OR ( resource IS NULL AND service <@ %(service)s AND event IS NULL AND "group"=%(group)s AND tags='{}' )
              OR ( resource IS NULL AND service <@ %(service)s AND event IS NULL AND "group"=%(group)s AND tags <@ %(tags)s )
              OR ( resource IS NULL AND service <@ %(service)s AND event=%(event)s AND "group" IS NULL AND tags='{}' )
              OR ( resource IS NULL AND service <@ %(service)s AND event=%(event)s AND "group" IS NULL AND tags <@ %(tags)s )
              OR ( resource IS NULL AND service <@ %(service)s AND event=%(event)s AND "group"=%(group)s AND tags='{}' )
              OR ( resource IS NULL AND service <@ %(service)s AND event=%(event)s AND "group"=%(group)s AND tags <@ %(tags)s )
              OR ( resource=%(resource)s AND service='{}' AND event IS NULL AND "group" IS NULL AND tags='{}' )
              OR ( resource=%(resource)s AND service='{}' AND event IS NULL AND "group" IS NULL AND tags <@ %(tags)s )
              OR ( resource=%(resource)s AND service='{}' AND event IS NULL AND "group"=%(group)s AND tags='{}' )
              OR ( resource=%(resource)s AND service='{}' AND event IS NULL AND "group"=%(group)s AND tags <@ %(tags)s )
              OR ( resource=%(resource)s AND service='{}' AND event=%(event)s AND "group" IS NULL AND tags='{}' )
              OR ( resource=%(resource)s AND service='{}' AND event=%(event)s AND "group" IS NULL AND tags <@ %(tags)s )
              OR ( resource=%(resource)s AND service='{}' AND event=%(event)s AND "group"=%(group)s AND tags='{}' )
              OR ( resource=%(resource)s AND service='{}' AND event=%(event)s AND "group"=%(group)s AND tags <@ %(tags)s )
              OR ( resource=%(resource)s AND service <@ %(service)s AND event IS NULL AND "group" IS NULL AND tags='{}' )
              OR ( resource=%(resource)s AND service <@ %(service)s AND event IS NULL AND "group" IS NULL AND tags <@ %(tags)s )
              OR ( resource=%(resource)s AND service <@ %(service)s AND event IS NULL AND "group"=%(group)s AND tags='{}' )
              OR ( resource=%(resource)s AND service <@ %(service)s AND event IS NULL AND "group"=%(group)s AND tags <@ %(tags)s )
              OR ( resource=%(resource)s AND service <@ %(service)s AND event=%(event)s AND "group" IS NULL AND tags='{}' )
              OR ( resource=%(resource)s AND service <@ %(service)s AND event=%(event)s AND "group" IS NULL AND tags <@ %(tags)s )
              OR ( resource=%(resource)s AND service <@ %(service)s AND event=%(event)s AND "group"=%(group)s AND tags='{}' )
              OR ( resource=%(resource)s AND service <@ %(service)s AND event=%(event)s AND "group"=%(group)s AND tags <@ %(tags)s )
                )
        """
        if current_app.config['CUSTOMER_VIEWS']:
            select += ' AND (customer IS NULL OR customer=%(customer)s)'
        if self._fetchone(select, vars(alert)):
            return True
        return False

    def update_blackout(self, id, **kwargs):
        update = """
            UPDATE blackouts
            SET
        """
        if kwargs.get('environment') is not None:
            update += 'environment=%(environment)s, '
        if 'service' in kwargs:
            update += 'service=%(service)s, '
        if 'resource' in kwargs:
            update += 'resource=%(resource)s, '
        if 'event' in kwargs:
            update += 'event=%(event)s, '
        if 'group' in kwargs:
            update += '"group"=%(group)s, '
        if 'tags' in kwargs:
            update += 'tags=%(tags)s, '
        if 'customer' in kwargs:
            update += 'customer=%(customer)s, '
        if kwargs.get('startTime') is not None:
            update += 'start_time=%(startTime)s, '
        if kwargs.get('endTime') is not None:
            update += 'end_time=%(endTime)s, '
        if 'duration' in kwargs:
            update += 'duration=%(duration)s, '
        if 'text' in kwargs:
            update += 'text=%(text)s, '
        update += """
            "user"=COALESCE(%(user)s, "user")
            WHERE id=%(id)s
            RETURNING *
        """
        kwargs['id'] = id
        kwargs['user'] = kwargs.get('user')
        return self._updateone(update, kwargs, returning=True)

    def delete_blackout(self, id):
        delete = """
            DELETE FROM blackouts
            WHERE id=%s
            RETURNING id
        """
        return self._deleteone(delete, (id,), returning=True)

    # HEARTBEATS

    def upsert_heartbeat(self, heartbeat):
        upsert = """
            INSERT INTO heartbeats (id, origin, tags, attributes, type, create_time, timeout, receive_time, customer)
            VALUES (%(id)s, %(origin)s, %(tags)s, %(attributes)s, %(event_type)s, %(create_time)s, %(timeout)s, %(receive_time)s, %(customer)s)
            ON CONFLICT (origin, COALESCE(customer, '')) DO UPDATE
                SET tags=%(tags)s, attributes=%(attributes)s, create_time=%(create_time)s, timeout=%(timeout)s, receive_time=%(receive_time)s
            RETURNING *
        """
        return self._upsert(upsert, vars(heartbeat))

    def get_heartbeat(self, id, customers=None):
        select = """
            SELECT * FROM heartbeats
             WHERE (id=%(id)s OR id LIKE %(like_id)s)
               AND {customer}
        """.format(customer='customer=%(customers)s' if customers else '1=1')
        return self._fetchone(select, {'id': id, 'like_id': id + '%', 'customers': customers})

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
        return self._deleteone(delete, {'id': id, 'like_id': id + '%'}, returning=True)

    # API KEYS

    def create_key(self, key):
        insert = """
            INSERT INTO keys (id, key, "user", scopes, text, expire_time, "count", last_used_time, customer)
            VALUES (%(id)s, %(key)s, %(user)s, %(scopes)s, %(text)s, %(expire_time)s, %(count)s, %(last_used_time)s, %(customer)s)
            RETURNING *
        """
        return self._insert(insert, vars(key))

    def get_key(self, key, user=None):
        select = """
            SELECT * FROM keys
             WHERE (id=%(key)s OR key=%(key)s)
               AND {user}
        """.format(user='"user"=%(user)s' if user else '1=1')
        return self._fetchone(select, {'key': key, 'user': user})

    def get_keys(self, query=None):
        query = query or Query()
        select = """
            SELECT * FROM keys
            WHERE {where}
        """.format(where=query.where)
        return self._fetchall(select, query.vars)

    def update_key(self, key, **kwargs):
        update = """
            UPDATE keys
            SET
        """
        if 'user' in kwargs:
            update += '"user"=%(user)s, '
        if 'scopes' in kwargs:
            update += 'scopes=%(scopes)s, '
        if 'text' in kwargs:
            update += 'text=%(text)s, '
        if 'expireTime' in kwargs:
            update += 'expire_time=%(expireTime)s, '
        if 'customer' in kwargs:
            update += 'customer=%(customer)s, '
        update += """
            id=id
            WHERE (id=%(key)s OR key=%(key)s)
            RETURNING *
        """
        kwargs['key'] = key
        return self._updateone(update, kwargs, returning=True)

    def update_key_last_used(self, key):
        update = """
            UPDATE keys
            SET last_used_time=NOW() at time zone 'utc', count=count + 1
            WHERE id=%s OR key=%s
        """
        return self._updateone(update, (key, key))

    def delete_key(self, key):
        delete = """
            DELETE FROM keys
            WHERE id=%s OR key=%s
            RETURNING key
        """
        return self._deleteone(delete, (key, key), returning=True)

    # USERS

    def create_user(self, user):
        insert = """
            INSERT INTO users (id, name, login, password, email, status, roles, attributes,
                create_time, last_login, text, update_time, email_verified)
            VALUES (%(id)s, %(name)s, %(login)s, %(password)s, %(email)s, %(status)s, %(roles)s, %(attributes)s, %(create_time)s,
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

    def get_user_by_username(self, username):
        select = """SELECT * FROM users WHERE login=%s OR email=%s"""
        return self._fetchone(select, (username, username))

    def get_user_by_email(self, email):
        select = """SELECT * FROM users WHERE email=%s"""
        return self._fetchone(select, (email,))

    def get_user_by_hash(self, hash):
        select = """SELECT * FROM users WHERE hash=%s"""
        return self._fetchone(select, (hash,))

    def update_last_login(self, id):
        update = """
            UPDATE users
            SET last_login=NOW() at time zone 'utc'
            WHERE id=%s
        """
        return self._updateone(update, (id,))

    def update_user(self, id, **kwargs):
        update = """
            UPDATE users
            SET
        """
        if kwargs.get('name', None) is not None:
            update += 'name=%(name)s, '
        if kwargs.get('login', None) is not None:
            update += 'login=%(login)s, '
        if kwargs.get('password', None) is not None:
            update += 'password=%(password)s, '
        if kwargs.get('email', None) is not None:
            update += 'email=%(email)s, '
        if kwargs.get('status', None) is not None:
            update += 'status=%(status)s, '
        if kwargs.get('roles', None) is not None:
            update += 'roles=%(roles)s, '
        if kwargs.get('attributes', None) is not None:
            update += 'attributes=attributes || %(attributes)s, '
        if kwargs.get('text', None) is not None:
            update += 'text=%(text)s, '
        if kwargs.get('email_verified', None) is not None:
            update += 'email_verified=%(email_verified)s, '
        update += """
            update_time=NOW() at time zone 'utc'
            WHERE id=%(id)s
            RETURNING *
        """
        kwargs['id'] = id
        return self._updateone(update, kwargs, returning=True)

    def update_user_attributes(self, id, old_attrs, new_attrs):
        from alerta.utils.collections import merge
        merge(old_attrs, new_attrs)
        attrs = {k: v for k, v in old_attrs.items() if v is not None}
        update = """
            UPDATE users
               SET attributes=%(attrs)s, update_time=NOW() at time zone 'utc'
             WHERE id=%(id)s
            RETURNING id
        """
        return bool(self._updateone(update, {'id': id, 'attrs': attrs}, returning=True))

    def delete_user(self, id):
        delete = """
            DELETE FROM users
            WHERE id=%s
            RETURNING id
        """
        return self._deleteone(delete, (id,), returning=True)

    def set_email_hash(self, id, hash):
        update = """
            UPDATE users
            SET hash=%s, update_time=NOW() at time zone 'utc'
            WHERE id=%s
        """
        return self._updateone(update, (hash, id))

    # GROUPS

    def create_group(self, group):
        insert = """
            INSERT INTO groups (id, name, text)
            VALUES (%(id)s, %(name)s, %(text)s)
            RETURNING *
        """
        return self._insert(insert, vars(group))

    def get_group(self, id):
        select = """SELECT * FROM groups WHERE id=%s"""
        return self._fetchone(select, (id,))

    def get_groups(self, query=None):
        query = query or Query()
        select = """
            SELECT * FROM groups
            WHERE {where}
        """.format(where=query.where)
        return self._fetchall(select, query.vars)

    def get_group_users(self, id):
        select = """
            SELECT u.id, u.login, u.email, u.name, u.status
              FROM (SELECT id, UNNEST(users) as uid FROM groups) g
            INNER JOIN users u on g.uid = u.id
            WHERE g.id = %s
        """
        return self._fetchall(select, (id,))

    def update_group(self, id, **kwargs):
        update = """
            UPDATE groups
            SET
        """
        if kwargs.get('name', None) is not None:
            update += 'name=%(name)s, '
        if kwargs.get('text', None) is not None:
            update += 'text=%(text)s, '
        update += """
            update_time=NOW() at time zone 'utc'
            WHERE id=%(id)s
            RETURNING *
        """
        kwargs['id'] = id
        return self._updateone(update, kwargs, returning=True)

    def add_user_to_group(self, group, user):
        update = """
            UPDATE groups
            SET users=ARRAY(SELECT DISTINCT UNNEST(users || %(users)s))
            WHERE id=%(id)s
            RETURNING *
        """
        return self._updateone(update, {'id': group, 'users': [user]}, returning=True)

    def remove_user_from_group(self, group, user):
        update = """
            UPDATE groups
            SET users=(select array_agg(u) FROM unnest(users) AS u WHERE NOT u=%(user)s )
            WHERE id=%(id)s
            RETURNING *
        """
        return self._updateone(update, {'id': group, 'user': user}, returning=True)

    def delete_group(self, id):
        delete = """
            DELETE FROM groups
            WHERE id=%s
            RETURNING id
        """
        return self._deleteone(delete, (id,), returning=True)

    def get_groups_by_user(self, user):
        select = """
            SELECT * FROM groups
            WHERE %s=ANY(users)
        """
        return self._fetchall(select, (user,))

    # PERMISSIONS

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

    def update_perm(self, id, **kwargs):
        update = """
            UPDATE perms
            SET
        """
        if 'match' in kwargs:
            update += 'match=%(match)s, '
        if 'scopes' in kwargs:
            update += 'scopes=%(scopes)s, '
        update += """
            id=%(id)s
            WHERE id=%(id)s
            RETURNING *
        """
        kwargs['id'] = id
        return self._updateone(update, kwargs, returning=True)

    def delete_perm(self, id):
        delete = """
            DELETE FROM perms
            WHERE id=%s
            RETURNING id
        """
        return self._deleteone(delete, (id,), returning=True)

    def get_scopes_by_match(self, login, matches):
        if login in current_app.config['ADMIN_USERS']:
            return ADMIN_SCOPES

        scopes = list()
        for match in matches:
            if match in current_app.config['ADMIN_ROLES']:
                return ADMIN_SCOPES
            if match in current_app.config['USER_ROLES']:
                scopes.extend(current_app.config['USER_DEFAULT_SCOPES'])
            if match in current_app.config['GUEST_ROLES']:
                scopes.extend(current_app.config['GUEST_DEFAULT_SCOPES'])
            select = """SELECT scopes FROM perms WHERE match=%s"""
            response = self._fetchone(select, (match,))
            if response:
                scopes.extend(response.scopes)
        return sorted(set(scopes))

    # CUSTOMERS

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

    def update_customer(self, id, **kwargs):
        update = """
            UPDATE customers
            SET
        """
        if 'match' in kwargs:
            update += 'match=%(match)s, '
        if 'customer' in kwargs:
            update += 'customer=%(customer)s, '
        update += """
            id=%(id)s
            WHERE id=%(id)s
            RETURNING *
        """
        kwargs['id'] = id
        return self._updateone(update, kwargs, returning=True)

    def delete_customer(self, id):
        delete = """
            DELETE FROM customers
            WHERE id=%s
            RETURNING id
        """
        return self._deleteone(delete, (id,), returning=True)

    def get_customers_by_match(self, login, matches):
        if login in current_app.config['ADMIN_USERS']:
            return '*'  # all customers

        customers = []
        for match in [login] + matches:
            select = """SELECT customer FROM customers WHERE match=%s"""
            response = self._fetchall(select, (match,))
            if response:
                customers.extend([r.customer for r in response])

        if customers:
            if '*' in customers:
                return '*'  # all customers
            return customers

        raise NoCustomerMatch("No customer lookup configured for user '{}' or '{}'".format(login, ','.join(matches)))

    # NOTES

    def create_note(self, note):
        insert = """
            INSERT INTO notes (id, text, "user", attributes, type,
                create_time, update_time, alert, customer)
            VALUES (%(id)s, %(text)s, %(user)s, %(attributes)s, %(note_type)s,
                %(create_time)s, %(update_time)s, %(alert)s, %(customer)s)
            RETURNING *
        """
        return self._insert(insert, vars(note))

    def get_note(self, id):
        select = """
            SELECT * FROM notes
            WHERE id=%s
        """
        return self._fetchone(select, (id,))

    def get_notes(self, query=None, page=None, page_size=None):
        query = query or Query()
        select = """
            SELECT * FROM notes
             WHERE {where}
          ORDER BY {order}
        """.format(where=query.where, order=query.sort or 'create_time')
        return self._fetchall(select, query.vars, limit=page_size, offset=(page - 1) * page_size)

    def get_alert_notes(self, id, page=None, page_size=None):
        select = """
            SELECT * FROM notes
             WHERE alert ~* (%s)
        """
        return self._fetchall(select, (id,), limit=page_size, offset=(page - 1) * page_size)

    def get_customer_notes(self, customer, page=None, page_size=None):
        select = """
            SELECT * FROM notes
             WHERE customer=%s
        """
        return self._fetchall(select, (customer,), limit=page_size, offset=(page - 1) * page_size)

    def update_note(self, id, **kwargs):
        update = """
            UPDATE notes
            SET
        """
        if kwargs.get('text', None) is not None:
            update += 'text=%(text)s, '
        if kwargs.get('attributes', None) is not None:
            update += 'attributes=attributes || %(attributes)s, '
        update += """
            "user"=COALESCE(%(user)s, "user"),
            update_time=NOW() at time zone 'utc'
            WHERE id=%(id)s
            RETURNING *
        """
        kwargs['id'] = id
        kwargs['user'] = kwargs.get('user')
        return self._updateone(update, kwargs, returning=True)

    def delete_note(self, id):
        delete = """
            DELETE FROM notes
            WHERE id=%s
            RETURNING id
        """
        return self._deleteone(delete, (id,), returning=True)

    # METRICS

    def get_metrics(self, type=None):
        select = """SELECT * FROM metrics"""
        if type:
            select += ' WHERE type=%s'
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
                SET count=metrics.count + %(count)s
            RETURNING *
        """
        return self._upsert(upsert, vars(counter))

    def update_timer(self, timer):
        upsert = """
            INSERT INTO metrics ("group", name, title, description, count, total_time, type)
            VALUES (%(group)s, %(name)s, %(title)s, %(description)s, %(count)s, %(total_time)s, %(type)s)
            ON CONFLICT ("group", name, type) DO UPDATE
                SET count=metrics.count + %(count)s, total_time=metrics.total_time + %(total_time)s
            RETURNING *
        """
        return self._upsert(upsert, vars(timer))

    # HOUSEKEEPING

    def get_expired(self, expired_threshold, info_threshold):
        # delete 'closed' or 'expired' alerts older than "expired_threshold" hours
        # and 'informational' alerts older than "info_threshold" hours

        if expired_threshold:
            delete = """
                DELETE FROM alerts
                 WHERE (status IN ('closed', 'expired')
                        AND last_receive_time < (NOW() at time zone 'utc' - INTERVAL '%(expired_threshold)s hours'))
            """
            self._deleteall(delete, {'expired_threshold': expired_threshold})

        if info_threshold:
            delete = """
                DELETE FROM alerts
                 WHERE (severity='informational'
                        AND last_receive_time < (NOW() at time zone 'utc' - INTERVAL '%(info_threshold)s hours'))
            """
            self._deleteall(delete, {'info_threshold': info_threshold})

        # get list of alerts to be newly expired
        select = """
            SELECT *
              FROM alerts
             WHERE status NOT IN ('expired') AND COALESCE(timeout, {timeout})!=0
               AND (last_receive_time + INTERVAL '1 second' * timeout) < NOW() at time zone 'utc'
        """.format(timeout=current_app.config['ALERT_TIMEOUT'])

        return self._fetchall(select, {})

    def get_unshelve(self):
        # get list of alerts to be unshelved
        select = """
            SELECT DISTINCT ON (a.id) a.*
              FROM alerts a, UNNEST(history) h
             WHERE a.status='shelved'
               AND h.type='shelve'
               AND h.status='shelved'
               AND COALESCE(h.timeout, {timeout})!=0
               AND (a.update_time + INTERVAL '1 second' * h.timeout) < NOW() at time zone 'utc'
          ORDER BY a.id, a.update_time DESC
        """.format(timeout=current_app.config['SHELVE_TIMEOUT'])
        return self._fetchall(select, {})

    def get_unack(self):
        # get list of alerts to be unack'ed
        select = """
            SELECT DISTINCT ON (a.id) a.*
              FROM alerts a, UNNEST(history) h
             WHERE a.status='ack'
               AND h.type='ack'
               AND h.status='ack'
               AND COALESCE(h.timeout, {timeout})!=0
               AND (a.update_time + INTERVAL '1 second' * h.timeout) < NOW() at time zone 'utc'
          ORDER BY a.id, a.update_time DESC
        """.format(timeout=current_app.config['ACK_TIMEOUT'])
        return self._fetchall(select, {})

    # SQL HELPERS

    def _insert(self, query, vars):
        """
        Insert, with return.
        """
        cursor = self.get_db().cursor()
        self._log(cursor, query, vars)
        cursor.execute(query, vars)
        self.get_db().commit()
        return cursor.fetchone()

    def _fetchone(self, query, vars):
        """
        Return none or one row.
        """
        cursor = self.get_db().cursor()
        self._log(cursor, query, vars)
        cursor.execute(query, vars)
        return cursor.fetchone()

    def _fetchall(self, query, vars, limit=None, offset=0):
        """
        Return multiple rows.
        """
        if limit is None:
            limit = current_app.config['DEFAULT_PAGE_SIZE']
        query += ' LIMIT %s OFFSET %s''' % (limit, offset)
        cursor = self.get_db().cursor()
        self._log(cursor, query, vars)
        cursor.execute(query, vars)
        return cursor.fetchall()

    def _updateone(self, query, vars, returning=False):
        """
        Update, with optional return.
        """
        cursor = self.get_db().cursor()
        self._log(cursor, query, vars)
        cursor.execute(query, vars)
        self.get_db().commit()
        return cursor.fetchone() if returning else None

    def _updateall(self, query, vars, returning=False):
        """
        Update, with optional return.
        """
        cursor = self.get_db().cursor()
        self._log(cursor, query, vars)
        cursor.execute(query, vars)
        self.get_db().commit()
        return cursor.fetchall() if returning else None

    def _upsert(self, query, vars):
        """
        Insert or update, with return.
        """
        return self._insert(query, vars)

    def _deleteone(self, query, vars, returning=False):
        """
        Delete, with optional return.
        """
        cursor = self.get_db().cursor()
        self._log(cursor, query, vars)
        cursor.execute(query, vars)
        self.get_db().commit()
        return cursor.fetchone() if returning else None

    def _deleteall(self, query, vars, returning=False):
        """
        Delete multiple rows, with optional return.
        """
        cursor = self.get_db().cursor()
        self._log(cursor, query, vars)
        cursor.execute(query, vars)
        self.get_db().commit()
        return cursor.fetchall() if returning else None

    def _log(self, cursor, query, vars):
        current_app.logger.debug('{stars}\n{query}\n{stars}'.format(
            stars='*' * 40, query=cursor.mogrify(query, vars).decode('utf-8')))
