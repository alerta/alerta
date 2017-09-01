import json
import re

from datetime import datetime, timedelta

import pytz

from flask import current_app, g

from alerta.app.utils.api import absolute_url

import psycopg2

from psycopg2.extras import NamedTupleCursor, register_composite
from psycopg2.extensions import register_adapter, adapt, AsIs

from alerta.app.models import status_code


# class InfDateAdapter:
#     def __init__(self, wrapped):
#         self.wrapped = wrapped
#     def getquoted(self):
#         if self.wrapped == datetime.date.max:
#             return b"'infinity'::date"
#         elif self.wrapped == datetime.date.min:
#             return b"'-infinity'::date"
#         else:
#             return psycopg2.extensions.DateFromPy(self.wrapped).getquoted()

# register_adapter(datetime.date, InfDateAdapter)

from alerta.app.utils.format import DateTime
from alerta.app.exceptions import NoCustomerMatch


# class DateTimeAdapter:
#     def __init__(self, dt):
#         self.dt = dt
#
#     def getquoted(self):
#         return b"'%s'::timestamptz" % DateTime.to_string(self.dt)

def adaptDict(d):
    return AsIs("'{%s}'" % ','.join(['{%s,%s}' % (k, v) for k, v in d.items()]))


def adaptDateTime(dt):
    return AsIs("%s" % adapt(DateTime.to_string(dt)))


class Backend:

    def create_engine(self, dsn, dbname=None):
        self.dsn = dsn
        self.dbname = dbname

    def connect(self):
        # > createdb alerta
        conn = psycopg2.connect(
            dsn=self.dsn,
            dbname=self.dbname,
            cursor_factory=NamedTupleCursor
        )
        # register_adapter(datetime, DateTimeAdapter)
        register_adapter(datetime, adaptDateTime)
        register_adapter(dict, adaptDict)

        self._register_history(conn)
        return conn

    # FIXME
    def _register_history(self, conn):
        from alerta.app.models.alert import History
        register_composite(
            'history',
            conn,
            globally=True
        )

        def adapt_history(h):
            return AsIs("(%s, %s, %s, %s, %s, %s, %s, %s)::history" % (
                    adapt(h.id).getquoted(),
                    adapt(h.event).getquoted(),
                    adapt(h.severity).getquoted(),
                    adapt(h.status).getquoted(),
                    adapt(h.value).getquoted(),
                    adapt(h.text).getquoted(),
                    adapt(h.change_type).getquoted(),
                    adapt(h.update_time).getquoted()
            ))

        register_adapter(History, adapt_history)

    @property
    def version(self):
        cursor = g.db.cursor()
        cursor.execute("SHOW server_version")
        return cursor.fetchone()

    @property
    def is_alive(self):
        cursor = g.db.cursor()
        cursor.execute("SELECT true")
        return cursor.fetchone()

    def close(self):
        g.db.close()

    def destroy(self, name=None):
        cursor = g.db.cursor()
        cursor.execute("SELECT current_database()")
        name = name or cursor.fetchone()
        cursor.execute("DROP DATABASE %s", (name,))  # FIXME -- this can't actually work, can it?

    @staticmethod
    def build_query(params):

        query_time = datetime.utcnow()

        # q
        if params.get('q', None):
            raise NotImplementedError("'q' search parameter is not currently supported")
        else:
            query = ['WHERE true=true']
            qvars = dict()

        # customer
        if g.get('customer', None):
            query.append('AND customer=%(customer)s')
            qvars['customer'] = g['customer']

        # from-date, to-date
        from_date = params.get('from-date', default=None, type=DateTime.parse)
        to_date = params.get('to-date', default=query_time, type=DateTime.parse)

        if from_date:
            query.append('AND last_receive_time > %(from_date)s')
            qvars['from_date'] = from_date.replace(tzinfo=pytz.utc)
        if to_date:
            query.append('AND last_receive_time <= %(to_date)s')
            qvars['to_date'] = to_date.replace(tzinfo=pytz.utc)

        # duplicateCount, repeat
        if params.get('duplicateCount', None):
            query.append('AND duplicate_count=%(duplicate_count)s')
            qvars['duplicate_count'] = params.get('duplicateCount', int)
        if params.get('repeat', None):
            query.append('AND repeat=%(repeat)s')
            qvars['repeat'] = params.get('repeat', default=True, type=lambda x: x.lower() in ['true', 't', '1', 'yes', 'y', 'on'])

        # sort-by
        sort = list()
        direction = 'ASC'
        if params.get('reverse', None):
            direction = 'DESC'

        if params.get('sort-by', None):
            for sort_by in params.getlist('sort-by'):
                if sort_by == 'createTime':
                    sort.append('create_time ' + ('ASC' if direction == 'DESC' else 'DESC'))
                elif sort_by == 'receiveTime':
                    sort.append('receive_time ' + ('ASC' if direction == 'DESC' else 'DESC'))
                elif sort_by == 'lastReceiveTime':
                    sort.append('last_receive_time ' + ('ASC' if direction == 'DESC' else 'DESC'))
                elif sort_by == 'duplicateCount':
                    sort.append('duplicate_count ' + direction)
                else:
                    sort.append(sort_by + ' ' + direction)

        # group-by
        group = params.getlist('group-by')

        # page, page-size, limit (deprecated)
        page = params.get('page', 1, int)
        limit = params.get('limit', current_app.config['DEFAULT_PAGE_SIZE'], int)
        page_size = params.get('page-size', limit, int)

        # id
        ids = params.getlist('id')
        if len(ids) == 1:
            query.append('AND (id LIKE %(id)s OR last_receive_id LIKE %(id)s)')
            qvars['id'] = ids[0]+'%'
        elif ids:
            query.append('AND (id ~* (%(regex_id)s) OR last_receive_id ~* (%(regex_id)s))')
            qvars['regex_id'] = '|'.join(['^' + i for i in ids])

        EXCLUDE_QUERY = ['q', 'id', 'from-date', 'to-date', 'duplicateCount', 'repeat',
                         'sort-by', 'reverse', 'group-by', 'page', 'page-size', 'limit']

        # fields
        for field in params:
            if field in EXCLUDE_QUERY:
                continue
            value = params.getlist(field)
            if len(value) == 1:
                value = value[0]
                if field.endswith('!'):
                    if value.startswith('~'):
                        query.append('AND NOT {0} ILIKE %(not_{0})s'.format(field[:-1]))
                        qvars['not_'+field[:-1]] = '%'+value[1:]+'%'
                    else:
                        query.append('AND {0}!=%(not_{0})s'.format(field[:-1]))
                        qvars['not_'+field[:-1]] = value
                else:
                    if value.startswith('~'):
                        query.append('AND {0} ILIKE %({0})s'.format(field))
                        qvars[field] = '%'+value[1:]+'%'
                    else:
                        query.append('AND {0}=%({0})s'.format(field))
                        qvars[field] = value
            else:
                if field.endswith('!'):
                    if '~' in [v[0] for v in value]:
                        query.append('AND {0} !~* (%(not_regex_{0})s)'.format(field[:-1]))
                        qvars['not_regex_'+field[:-1]] = '|'.join([v.lstrip('~') for v in value])
                    else:
                        query.append('AND NOT {0}=ANY(%(not_{0})s)'.format(field[:-1]))
                        qvars['not_'+field[:-1]] = value
                else:
                    if '~' in [v[0] for v in value]:
                        query.append('AND {0} ~* (%(regex_{0})s)'.format(field))
                        qvars['regex_'+field] = '|'.join([v.lstrip('~') for v in value])
                    else:
                        query.append('AND {0}=ANY(%({0})s)'.format(field))
                        qvars[field] = value

        return ('\n'.join(query), qvars), ', '.join(sort), group, page, page_size, query_time

    #### ALERTS

    def get_severity(self, alert):
        query = """
            SELECT severity FROM alerts
             WHERE environment=%(environment)s AND resource=%(resource)s
               AND ((event=%(event)s AND severity!=%(severity)s)
                OR (event!=%(event)s AND %(event)s=ANY(correlate)))
            """
        if alert.customer:
            query += "AND CUSTOMER=%(customer)s"
        cursor = g.db.cursor()
        cursor.execute(query, vars(alert))
        return cursor.fetchone()

    def get_status(self, alert):
        query = """
            SELECT status FROM alerts
             WHERE environment=%(environment)s AND resource=%(resource)s
               AND (event=%(event)s OR %(event)s=ANY(correlate))
            """
        if alert.customer:
            query += "AND CUSTOMER=%(customer)s"
        cursor = g.db.cursor()
        cursor.execute(query, vars(alert))
        return cursor.fetchone()

    def is_duplicate(self, alert):
        query = """
            SELECT id FROM alerts
             WHERE environment=%(environment)s
               AND resource=%(resource)s
               AND event=%(event)s
               AND severity=%(severity)s
            """
        if alert.customer:
            query += "AND CUSTOMER=%(customer)s"
        cursor = g.db.cursor()
        cursor.execute(query, vars(alert))
        return bool(cursor.fetchone())

    def is_correlated(self, alert):
        query = """
            SELECT id FROM alerts
             WHERE environment=%(environment)s AND resource=%(resource)s
               AND ((event=%(event)s AND severity!=%(severity)s)
                OR (event!=%(event)s AND %(event)s=ANY(correlate)))
        """
        if alert.customer:
            query += "AND CUSTOMER=%(customer)s"
        cursor = g.db.cursor()
        cursor.execute(query, vars(alert))
        return bool(cursor.fetchone())

    def is_flapping(self, alert, window=1800, count=2):
        query = """
            SELECT COUNT(*)
              FROM alerts, unnest(history) h
             WHERE environment=%(environment)s
               AND resource=%(resource)s
               AND event=%(event)s
               AND h.update_time > {window}
               AND h.type=="severity"
        """.format(window=(datetime.utcnow() - timedelta(seconds=window)))
        cursor = g.db.cursor()
        cursor.execute(query, vars(alert))
        return cursor.fetchone() > count

    def dedup_alert(self, alert, history):
        """
        Update alert value, text and rawData, increment duplicate count and set repeat=True, and
        keep track of last receive id and time but don't append to history unless status changes.
        """
        # FIXME
        # old_attrs.update(new_attrs)
        # attrs = dict([k, v] for k, v in old_attrs.items() if v is not None)

        alert.repeat = True
        alert.last_receive_id = alert.id
        alert.last_receive_time = datetime.utcnow()
        alert.history = history  # append new history to existing
        update = """
            UPDATE alerts
               SET status=%(status)s, value=%(value)s, text=%(text)s, raw_data=%(raw_data)s, repeat=%(repeat)s,
                   last_receive_id=%(last_receive_id)s, last_receive_time=%(last_receive_time)s,
                   tags=ARRAY(SELECT DISTINCT UNNEST(tags || %(tags)s)), attributes=%(attributes)s,
                   duplicate_count=duplicate_count+1, history=(history || %(history)s)[:{limit}]
             WHERE environment=%(environment)s
               AND resource=%(resource)s
               AND event=%(event)s
               AND severity=%(severity)s
               AND (customer IS NULL OR customer=%(customer)s)
         RETURNING *
        """.format(limit=current_app.config['HISTORY_LIMIT'])
        cursor = g.db.cursor()
        print(cursor.mogrify(update, vars(alert)))
        cursor.execute(update, vars(alert))
        g.db.commit()
        return cursor.fetchone()

    def correlate_alert(self, alert, history):

        alert.repeat = False
        alert.history = history
        update = """
            UPDATE alerts
               SET event=%(event)s, severity=%(severity)s, status=%(status)s, value=%(value)s, text=%(text)s,
                   create_time=%(create_time)s, raw_data=%(raw_data)s, duplicate_count=0, repeat=false,
                   previous_severity=%(previous_severity)s, trend_indication=%(trend_indication)s,
                   receive_time=%(receive_time)s, last_receive_id=%(last_receive_id)s,
                   last_receive_time=%(last_receive_time)s, tags=ARRAY(SELECT DISTINCT UNNEST(tags || %(tags)s)),
                   history=(history || %(history)s)[:{limit}]
             WHERE environment=%(environment)s
               AND resource=%(resource)s
               AND ((event=%(event)s AND severity!=%(severity)s) OR (event!=%(event)s AND %(event)s=ANY(correlate)))
               AND (customer IS NULL OR customer=%(customer)s)
         RETURNING *
        """.format(limit=current_app.config['HISTORY_LIMIT'])
        cursor = g.db.cursor()
        print(cursor.mogrify(update, vars(alert)))
        cursor.execute(update, vars(alert))
        g.db.commit()
        return cursor.fetchone()

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
        data = vars(alert)
        data['attributes'] = [list(a) for a in alert.attributes.items()]

        cursor = g.db.cursor()
        print(cursor.mogrify(insert, data))
        cursor.execute(insert, data)
        g.db.commit()
        return cursor.fetchone()

    def get_alert(self, id, customer=None):
        query = "SELECT * FROM alerts WHERE id=%(id)s"
        if customer:
            query += " AND CUSTOMER=%(customer)s"
        cursor = g.db.cursor()
        cursor.execute(query, {'id': id, 'customer': customer})
        return cursor.fetchone()

    #### STATUS, TAGS, ATTRIBUTES

    def set_status(self, id, status, history=None):
        # FIXME use current_app.config['HISTORY_LIMIT']
        update = """
            UPDATE alerts
               SET status=%(status)s,
                   history=(history || %(change)s)[:2]
            WHERE id=%(id)s OR id LIKE %(like_id)s
            RETURNING *
        """
        cursor = g.db.cursor()
        print(cursor.mogrify(update, {'id': id, 'like_id': id + '%', 'status': status, 'change': history}))
        cursor.execute(update, {'id': id, 'like_id': id + '%', 'status': status, 'change': history})
        g.db.commit()
        return cursor.fetchone()

    def tag_alert(self, id, tags):
        update = """
            UPDATE alerts
            SET tags=ARRAY(SELECT DISTINCT UNNEST(tags || %(tags)s))
            WHERE id=%(id)s OR id LIKE %(like_id)s
            RETURNING *
        """
        cursor = g.db.cursor()
        print(cursor.mogrify(update, {'id': id, 'like_id': id+'%', 'tags': tags}))
        cursor.execute(update, {'id': id, 'like_id': id+'%', 'tags': tags})
        g.db.commit()
        return cursor.fetchone()

    def untag_alert(self, id, tags):
        update = """
            UPDATE alerts
            SET tags=(select array_agg(t) FROM unnest(tags) AS t WHERE NOT t=ANY(%(tags)s) )
            WHERE id=%(id)s OR id LIKE %(like_id)s
            RETURNING *
        """
        cursor = g.db.cursor()
        print(cursor.mogrify(update, {'id': id, 'like_id': id+'%', 'tags': tags}))
        cursor.execute(update, {'id': id, 'like_id': id+'%', 'tags': tags})
        g.db.commit()
        return cursor.fetchone()

    def update_attributes(self, id, old_attrs, new_attrs):
        old_attrs.update(new_attrs)
        attrs = dict([k, v] for k, v in old_attrs.items() if v is not None)
        print(attrs)
        update = """
            UPDATE alerts
               SET attributes=%(attrs)s
            RETURNING *
        """
        cursor = g.db.cursor()
        print(cursor.mogrify(update, {'id': id, 'like_id': id+'%', 'attrs': attrs}))
        cursor.execute(update, {'id': id, 'like_id': id+'%', 'attrs': attrs})
        g.db.commit()
        return cursor.fetchone()

    def delete_alert(self, id):
        delete = """
            DELETE FROM alerts
            WHERE id=%(id)s OR id LIKE %(like_id)s
            RETURNING id
        """
        cursor = g.db.cursor()
        cursor.execute(delete, {'id': id, 'like_id': id+'%'})
        g.db.commit()
        return cursor.fetchone()

    #### SEARCH & HISTORY

    def get_alerts(self, query, sort, page, page_size):
        where, qvars = query

        query = """SELECT * FROM alerts """
        query += where + ' \n'
        query += """ORDER BY {0} OFFSET {1} LIMIT {2}""".format(sort, (page - 1) * page_size, page_size)

        cursor = g.db.cursor()

        # print(cursor.mogrify(query, (sort, (page - 1) * page_size, page_size)))
        # cursor.execute(query, (sort, (page - 1) * page_size, page_size))
        print(cursor.mogrify(query, qvars))
        cursor.execute(query, qvars)
        return cursor.fetchall()

    def get_history(self, query, page, page_size):
        # FIXME query filter
        query = """
            SELECT resource, environment, correlate, service, "group", tags, attributes, origin, create_time,
                timeout, raw_data, customer, duplicate_count, repeat, previous_severity, trend_indication,
                receive_time, last_receive_id, last_receive_time, history, h.* from alerts, unnest(history) h
            OFFSET %s LIMIT %s
        """
        cursor = g.db.cursor()
        print(cursor.mogrify(query, ((page - 1) * page_size, page_size)))
        cursor.execute(query, ((page - 1) * page_size, page_size))
        return cursor.fetchall()

    #### COUNTS

    def get_count(self, query=None):
        # FIXME query filter
        query = """SELECT COUNT(1) FROM alerts"""
        cursor = g.db.cursor()
        cursor.execute(query)
        return cursor.fetchone()

    def get_counts_by_severity(self, query=None):
        # FIXME query
        query = """SELECT severity, COUNT(*) FROM alerts GROUP BY severity"""
        cursor = g.db.cursor()
        cursor.execute(query)
        return dict([(s.severity, s.count) for s in cursor.fetchall()])

    def get_counts_by_status(self, query=None):
        # FIXME query
        query = """SELECT status, COUNT(*) FROM alerts GROUP BY status"""
        cursor = g.db.cursor()
        cursor.execute(query)
        return dict([(s.status, s.count) for s in cursor.fetchall()])

    def get_topn_count(self, query=None, group="event", topn=10):
        # FIXME query & group
        query = """
            SELECT event, COUNT(1) as count, SUM(duplicate_count) AS duplicate_count,
                   array_agg(DISTINCT environment) AS environments, array_agg(DISTINCT svc) AS services,
                   array_agg(DISTINCT ARRAY[id, resource]) AS resources
              FROM alerts, UNNEST (service) svc
          GROUP BY event
          ORDER BY count DESC
             LIMIT %s
        """
        cursor = g.db.cursor()
        print(cursor.mogrify(query, (topn,)))
        cursor.execute(query, (topn,))
        return [
            {
                "count": t.count,
                "duplicateCount": t.duplicate_count,
                "environments": t.environments,
                "event": t.event,
                "resources": [{"id": r[0], "resource": r[1], "href": absolute_url('/alert/%s' % r[0])} for r in t.resources]
            } for t in cursor.fetchall()
        ]

    def get_topn_flapping(self, query=None, group="event", topn=10):
        # FIXME query & group
        query = """
            SELECT alerts.event, COUNT(1) as count, SUM(duplicate_count) AS duplicate_count,
                   array_agg(DISTINCT environment) AS environments, array_agg(DISTINCT svc) AS services,
                   array_agg(DISTINCT ARRAY[alerts.id, resource]) AS resources
              FROM alerts, UNNEST (service) svc, UNNEST (history) hist
             WHERE hist.type='severity'
          GROUP BY alerts.event
          ORDER BY count DESC
             LIMIT %s
        """
        cursor = g.db.cursor()
        print(cursor.mogrify(query, (topn,)))
        cursor.execute(query, (topn,))
        return [
            {
                "count": t.count,
                "duplicateCount": t.duplicate_count,
                "environments": t.environments,
                "event": t.event,
                "resources": [{"id": r[0], "resource": r[1], "href": absolute_url('/alert/%s' % r[0])} for r in t.resources]
            } for t in cursor.fetchall()
        ]

    #### ENVIRONMENTS

    def get_environments(self, query=None, topn=100):
        query = """SELECT environment, count(1) FROM alerts GROUP BY environment"""
        cursor = g.db.cursor()
        cursor.execute(query)
        return [{"environment": e.environment, "count": e.count} for e in cursor.fetchall()]

    #### SERVICES

    def get_services(self, query=None, topn=100):
        query = """SELECT environment, svc, count(1) FROM alerts, UNNEST(service) svc GROUP BY environment, svc"""
        cursor = g.db.cursor()
        cursor.execute(query)
        return [{"environment": s.environment, "service": s.svc, "count": s.count} for s in cursor.fetchall()]

    #### BLACKOUTS

    def create_blackout(self, blackout):
        insert = """
            INSERT INTO blackouts (id, priority, environment, service, resource, event, "group", tags, customer, start_time, end_time, duration)
            VALUES (%(id)s, %(priority)s, %(environment)s, %(service)s, %(resource)s, %(event)s, %(group)s, %(tags)s, %(customer)s, %(start_time)s, %(end_time)s, %(duration)s)
            RETURNING *
        """
        cursor = g.db.cursor()
        print(cursor.mogrify(insert, vars(blackout)))
        cursor.execute(insert, vars(blackout))
        g.db.commit()
        return cursor.fetchone()

    def get_blackout(self, id, customer=None):
        query = "SELECT * FROM blackouts WHERE id=%(id)s"
        if customer:
            query += " AND CUSTOMER=%(customer)s"
        cursor = g.db.cursor()
        cursor.execute(query, {'id': id, 'customer': customer})
        return cursor.fetchone()

    def get_blackouts(self, query, page, page_size):
        # FIXME - query support filter by user
        query = """
            SELECT * FROM blackouts
            LIMIT %(limit)s
            OFFSET %(offset)s
        """
        cursor = g.db.cursor()
        cursor.execute(query, {'limit': page_size, 'offset': (page - 1) * page_size})
        return cursor.fetchall()

    def is_blackout_period(self, alert):
        now = datetime.utcnow()
        query = """
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
        cursor = g.db.cursor()
        print(cursor.mogrify(query, data))
        cursor.execute(query, data)
        if cursor.fetchone():
            return True
        if current_app.config['CUSTOMER_VIEWS']:
            query += " AND CUSTOMER=%(customer)s"
            if cursor.fetchone():
                return True
        return False

    def delete_blackout(self, id):
        delete = """
            DELETE FROM blackouts
            WHERE id=%s
            RETURNING id
        """
        cursor = g.db.cursor()
        cursor.execute(delete, (id,))
        g.db.commit()
        return cursor.fetchone()

    #### HEARTBEATS

    def upsert_heartbeat(self, heartbeat):
        upsert = """
            INSERT INTO heartbeats (id, origin, tags, type, create_time, timeout, receive_time, customer)
            VALUES (%(id)s, %(origin)s, %(tags)s, %(event_type)s, %(create_time)s, %(timeout)s, %(receive_time)s, %(customer)s)
            ON CONFLICT (origin, COALESCE(customer, '')) DO UPDATE
                SET tags=%(tags)s, timeout=%(timeout)s, receive_time=%(receive_time)s
            RETURNING *
        """
        cursor = g.db.cursor()
        print(cursor.mogrify(upsert, vars(heartbeat)))
        cursor.execute(upsert, vars(heartbeat))
        g.db.commit()
        return cursor.fetchone()

    def get_heartbeat(self, id, customer=None):
        query = "SELECT * FROM heartbeats WHERE id=%(id)s OR id LIKE %(like_id)s"
        if customer:
            query += " AND CUSTOMER=%(customer)s"
        cursor = g.db.cursor()
        print(cursor.mogrify(query, {'id': id, 'like_id': id+'%', 'customer': customer}))
        cursor.execute(query, {'id': id, 'like_id': id+'%', 'customer': customer})
        return cursor.fetchone()

    def get_heartbeats(self, query, page, page_size):
        # FIXME - query support filter by user
        query = """
            SELECT * FROM heartbeats
            LIMIT %(limit)s
            OFFSET %(offset)s
        """
        cursor = g.db.cursor()
        cursor.execute(query, {'limit': page_size, 'offset': (page - 1) * page_size})
        return cursor.fetchall()

    def delete_heartbeat(self, id):
        delete = """
            DELETE FROM heartbeats
            WHERE id=%(id)s OR id LIKE %(like_id)s
            RETURNING id
        """
        cursor = g.db.cursor()
        cursor.execute(delete, {'id': id, 'like_id': id+'%'})
        g.db.commit()
        return cursor.fetchone()

    #### API KEYS

    def create_key(self, key):
        insert = """
            INSERT INTO keys (id, key, "user", scopes, text, expire_time, "count", last_used_time, hash, customer)
            VALUES (%(id)s, %(key)s, %(user)s, %(scopes)s, %(text)s, %(expire_time)s, %(count)s, %(last_used_time)s, %(hash)s, %(customer)s)
            RETURNING *
        """
        cursor = g.db.cursor()
        # print(cursor.mogrify(insert, vars(key)))
        cursor.execute(insert, vars(key))
        g.db.commit()
        return cursor.fetchone()

    def get_key(self, id, customer=None):
        query = "SELECT * FROM keys WHERE id=%(id)s"
        if customer:
            query += " AND CUSTOMER=%(customer)s"
        cursor = g.db.cursor()
        cursor.execute(query, {'id': id, 'customer': customer})
        return cursor.fetchone()

    def get_keys(self, query, page, page_size):
        # FIXME - query support filter by user
        query = """
            SELECT * FROM keys
            LIMIT %(limit)s
            OFFSET %(offset)s
        """
        cursor = g.db.cursor()
        cursor.execute(query, {'limit': page_size, 'offset': (page - 1) * page_size})
        return cursor.fetchall()

    def update_key_last_used(self, key):
        update = """
            UPDATE keys
            SET last_used_time=%s, count=count+1
            WHERE key=%s
        """
        # print(cursor.mogrify(update, (datetime.utcnow(), key)))
        cursor = g.db.cursor()
        cursor.execute(update, (datetime.utcnow(), key))
        return g.db.commit()

    def delete_key(self, id):
        delete = """
            DELETE FROM keys
            WHERE id=%s
            RETURNING key
        """
        cursor = g.db.cursor()
        cursor.execute(delete, (id,))
        g.db.commit()
        return cursor.fetchone()

    #### USERS

    def create_user(self, user):
        insert = """
            INSERT INTO users (id, name, password, email, create_time, last_login, text, email_verified)
            VALUES (%(id)s, %(name)s, %(password)s, %(email)s, %(create_time)s, %(last_login)s, %(text)s, %(email_verified)s)
            RETURNING *
        """
        # print(cursor.mogrify(insert, vars(user)))
        cursor = g.db.cursor()
        cursor.execute(insert, vars(user))
        g.db.commit()
        return cursor.fetchone()

    def get_user(self, id):
        query = "SELECT * FROM users WHERE id=%s"
        cursor = g.db.cursor()
        cursor.execute(query, (id,))
        return cursor.fetchone()

    def get_users(self, query, page, page_size):
        # FIXME - query support filter by user
        query = """
            SELECT * FROM users
            LIMIT %(limit)s
            OFFSET %(offset)s
        """
        cursor = g.db.cursor()
        cursor.execute(query, {'limit': page_size, 'offset': (page - 1) * page_size})
        return cursor.fetchall()

    def get_user_by_email(self, email):
        query = "SELECT * FROM users WHERE email=%s"
        cursor = g.db.cursor()
        cursor.execute(query, (email,))
        return cursor.fetchone()

    def get_user_by_hash(self, hash):
        query = "SELECT * FROM users WHERE hash=%s"
        cursor = g.db.cursor()
        cursor.execute(query, (hash,))
        return cursor.fetchone()

    def update_last_login(self, id):
        update = """
            UPDATE users
            SET last_login=%s
            WHERE id=%s
        """
        cursor = g.db.cursor()
        # print(cursor.mogrify(update, (datetime.utcnow(), id)))
        cursor.execute(update, (datetime.utcnow(), id))
        return g.db.commit()

    def set_email_hash(self, id, hash):
        update = """
            UPDATE users
            SET hash=%(hash)s
            WHERE id=%(id)s
        """
        cursor = g.db.cursor()
        # print(cursor.mogrify(update, (datetime.utcnow(), id)))
        cursor.execute(update, {'id': id, 'hash': hash})
        return g.db.commit()

    def update_user(self, id, **kwargs):
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
        if 'role' in kwargs:
            update += "role=%(role)s, "
        if 'text' in kwargs:
            update += "text=%(text)s, "
        if 'email_verified' in kwargs:
            update += "email_verified=%(email_verified)s, "
        update += """
            id=%(id)s
            WHERE id=%(id)s
            RETURNING *
        """
        kwargs['id'] = id
        cursor = g.db.cursor()
        print(cursor.mogrify(update, kwargs))
        cursor.execute(update, kwargs)
        g.db.commit()
        return cursor.fetchone()

    def delete_user(self, id):
        delete = """
            DELETE FROM users
            WHERE id=%s
            RETURNING id
        """
        cursor = g.db.cursor()
        # print(cursor.mogrify(delete, (id,)))
        cursor.execute(delete, (id,))
        g.db.commit()
        return cursor.fetchone()

    #### PERMISSIONS

    def create_perm(self, perm):
        insert = """
            INSERT INTO perms (id, match, scopes)
            VALUES (%(id)s, %(match)s, %(scopes)s)
            RETURNING *
        """
        cursor = g.db.cursor()
        # print(cursor.mogrify(insert, vars(perm)))
        cursor.execute(insert, vars(perm))
        g.db.commit()
        return cursor.fetchone()

    def get_perm(self, id):
        query = "SELECT * FROM perms WHERE id=%s"
        cursor = g.db.cursor()
        cursor.execute(query, (id,))
        return cursor.fetchone()

    def get_perms(self, query, page, page_size):
        # FIXME - query support filter by user
        query = """
            SELECT * FROM perms
            LIMIT %(limit)s
            OFFSET %(offset)s
        """
        cursor = g.db.cursor()
        cursor.execute(query, {'limit': page_size, 'offset': (page - 1) * page_size})
        return cursor.fetchall()

    def delete_perm(self, id):
        delete = """
            DELETE FROM perms
            WHERE id=%s
            RETURNING id
        """
        cursor = g.db.cursor()
        # print(cursor.mogrify(delete, (id,)))
        cursor.execute(delete, (id,))
        g.db.commit()
        return cursor.fetchone()

    def get_scopes_by_match(self, login, matches):
        if login in current_app.config['ADMIN_USERS']:
            return ['admin', 'read', 'write']

        scopes = list()
        for match in matches:
            cursor = g.db.cursor()
            cursor.execute("""SELECT scopes FROM perms WHERE match=%s""" % (match,))
            response = cursor.fetchone()
            print(response)
            if response:
                scopes.extend(response['scopes'])
        return set(scopes) or current_app.config['USER_DEFAULT_SCOPES']

    #### CUSTOMERS

    def create_customer(self, customer):
        insert = """
            INSERT INTO customers (id, match, customer)
            VALUES (%(id)s, %(match)s, %(customer)s)
            RETURNING *
        """
        cursor = g.db.cursor()
        print(cursor.mogrify(insert, vars(customer)))
        cursor.execute(insert, vars(customer))
        g.db.commit()
        return cursor.fetchone()

    def get_customer(self, id):
        query = "SELECT * FROM customers WHERE id=%s"
        cursor = g.db.cursor()
        cursor.execute(query, (id,))
        return cursor.fetchone()

    def get_customers(self, query, page, page_size):
        # FIXME - query support filter by user
        query = """
            SELECT * FROM customers
            LIMIT %(limit)s
            OFFSET %(offset)s
        """
        cursor = g.db.cursor()
        cursor.execute(query, {'limit': page_size, 'offset': (page - 1) * page_size})
        return cursor.fetchall()

    def delete_customer(self, id):
        delete = """
            DELETE FROM customers
            WHERE id=%s
            RETURNING id
        """
        cursor = g.db.cursor()
        print(cursor.mogrify(delete, (id,)))
        cursor.execute(delete, (id,))
        g.db.commit()
        return cursor.fetchone()

    def get_customers_by_match(self, login, matches):
        if login in current_app.config['ADMIN_USERS']:
            return '*'  # all customers

        for match in [login] + matches:
            cursor = g.db.cursor()
            cursor.execute("""SELECT customer FROM users WHERE match=%s""" % (match,))
            response = cursor.fetchone()
            if response:
                return response['customer']
        raise NoCustomerMatch("No customer lookup configured for user '%s' or '%s'" % (login, ','.join(matches)))

    #### METRICS

    def get_metrics(self, type=None):
        query = """
            SELECT * FROM metrics
        """
        if type:
            query += " WHERE type=%(type)s"
        cursor = g.db.cursor()
        print(cursor.mogrify(query, {'type': type}))
        cursor.execute(query, {'type': type})
        return cursor.fetchall()

    def set_gauge(self, gauge):
        print(gauge)
        upsert = """
            INSERT INTO metrics ("group", name, title, description, value, type)
            VALUES (%(group)s, %(name)s, %(title)s, %(description)s, %(value)s, %(type)s)
            ON CONFLICT ("group", name, type) DO UPDATE
                SET value=%(value)s
            RETURNING *
        """
        cursor = g.db.cursor()
        print(cursor.mogrify(upsert, vars(gauge)))
        cursor.execute(upsert, vars(gauge))
        g.db.commit()
        return cursor.fetchone()

    def inc_counter(self, counter):
        upsert = """
            INSERT INTO metrics ("group", name, title, description, count, type)
            VALUES (%(group)s, %(name)s, %(title)s, %(description)s, %(count)s, %(type)s)
            ON CONFLICT ("group", name, type) DO UPDATE
                SET count=metrics.count+%(count)s
            RETURNING *
        """
        cursor = g.db.cursor()
        print(cursor.mogrify(upsert, vars(counter)))
        cursor.execute(upsert, vars(counter))
        g.db.commit()
        return cursor.fetchone()

    def update_timer(self, timer):
        upsert = """
            INSERT INTO metrics ("group", name, title, description, count, total_time, type)
            VALUES (%(group)s, %(name)s, %(title)s, %(description)s, %(count)s, %(total_time)s, %(type)s)
            ON CONFLICT ("group", name, type) DO UPDATE
                SET count=metrics.count+%(count)s, total_time=metrics.total_time+%(total_time)s
            RETURNING *
        """
        cursor = g.db.cursor()
        print(cursor.mogrify(upsert, vars(timer)))
        cursor.execute(upsert, vars(timer))
        g.db.commit()
        return cursor.fetchone()
