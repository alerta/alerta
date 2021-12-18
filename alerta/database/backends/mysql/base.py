import json
import threading
import time
from collections import defaultdict, namedtuple
from urllib.parse import urlparse

import pymysql
from flask import current_app
from pymysql.constants import CLIENT

from alerta.app import alarm_model
from alerta.database.base import Database
from alerta.exceptions import NoCustomerMatch
from alerta.models.enums import ADMIN_SCOPES
from alerta.models.heartbeat import HeartbeatStatus
from alerta.utils.format import custom_json_dumps
from alerta.utils.response import absolute_url

from .utils import Query

MAX_RETRIES = 5

Record = namedtuple('Record', [
    'id', 'resource', 'event', 'environment', 'severity', 'status', 'service',
    'group', 'value', 'text', 'tags', 'attributes', 'origin', 'update_time',
    'user', 'timeout', 'type', 'customer'
])


class Backend(Database):
    def create_engine(self, app, uri, dbname=None, raise_on_error=True):
        self.uri = uri
        self.dbname = dbname

        lock = threading.Lock()
        with lock:
            conn = self.connect()
            with app.open_resource('sql/mysql-schema.sql') as f:
                try:
                    queries = f.read().decode('utf-8')
                    conn.cursor().execute(queries)
                    conn.commit()
                except Exception as e:
                    if raise_on_error:
                        raise
                    app.logger.warning(e)

    def connect(self):
        retry = 0
        url = urlparse(self.uri)
        while True:
            try:
                conn = pymysql.connect(
                    user=url.username,
                    password=url.password,
                    host=url.hostname,
                    port=url.port,
                    database=url.path.lstrip('/'),
                    charset='utf8',
                    client_flag=CLIENT.MULTI_STATEMENTS,
                    cursorclass=pymysql.cursors.DictCursor
                )
                break
            except Exception as e:
                print(e)  # FIXME - should log this error instead of printing, but current_app is unavailable here
                retry += 1
                if retry > MAX_RETRIES:
                    conn = None
                    break
                else:
                    backoff = 2 ** retry
                    print(f'Retry attempt {retry}/{MAX_RETRIES} (wait={backoff}s)...')
                    time.sleep(backoff)

        if conn:
            return conn
        else:
            raise RuntimeError(f'Database connect error. Failed to connect after {MAX_RETRIES} retries.')

    @property
    def name(self):
        cursor = self.get_db().cursor()
        cursor.execute('SELECT database()')
        return cursor.fetchone()[0]

    @property
    def version(self):
        cursor = self.get_db().cursor()
        cursor.execute('SELECT version()')
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
        for table in ['alerts', 'blackouts', 'customers', 'groups', 'heartbeats', 'keys', 'metrics', 'perms', 'users']:
            conn.cursor().execute(f'DROP TABLE IF EXISTS `{table}`')
        conn.close()

    # ALERTS

    def _distinct_tag_query(self, tag_var='tags'):
        return f"""
            SELECT IFNULL(json_arrayagg(tag), '[]')
            FROM
            (SELECT DISTINCT t.tag
            FROM JSON_TABLE(JSON_MERGE(
                    IFNULL(alerts.tags, '[]'), IFNULL(%({tag_var})s, '[]')),
                    "$[*]" columns (tag varchar(255) PATH "$")
                ) t) AS TEMP
        """

    def _format_alert(self, alert):
        if alert:
            row = {
                **alert,
                'attributes': json.loads(alert['attributes']),
                'service': json.loads(alert['service']),
                'tags': json.loads(alert['tags']),
                'correlate': json.loads(alert['correlate']),
                'history': json.loads(alert['history']),
                'raw_data': alert['raw_data'] and json.loads(alert['raw_data'])
            }
            named_tuple = namedtuple('alert', row.keys())
            return named_tuple(*row.values())

    def _get_alert_by_id(self, vars):
        select = """
            SELECT * FROM alerts
             WHERE id=%(id)s OR id LIKE %(like_id)s
        """
        alert = self._fetchone(select, vars)
        return self._format_alert(alert)

    def get_severity(self, alert):
        select = """
            SELECT severity FROM alerts
             WHERE environment=%(environment)s AND resource=%(resource)s
               AND ((event=%(event)s AND severity!=%(severity)s)
               OR (event!=%(event)s AND JSON_CONTAINS(correlate, JSON_QUOTE(%(event)s))))
               AND {customer}
            """.format(customer='customer=%(customer)s' if alert.customer else 'customer IS NULL')
        return self._fetchone(select, self._vars(alert))['severity']

    def get_status(self, alert):
        select = """
            SELECT status FROM alerts
             WHERE environment=%(environment)s AND resource=%(resource)s
              AND (event=%(event)s OR JSON_CONTAINS(correlate, JSON_QUOTE(%(event)s)))
              AND {customer}
            """.format(customer='customer=%(customer)s' if alert.customer else 'customer IS NULL')
        return self._fetchone(select, self._vars(alert))['status']

    def is_duplicate(self, alert):
        select = """
            SELECT * FROM alerts
             WHERE environment=%(environment)s
               AND resource=%(resource)s
               AND event=%(event)s
               AND severity=%(severity)s
               AND {customer}
            """.format(customer='customer=%(customer)s' if alert.customer else 'customer IS NULL')
        alert_record = self._fetchone(select, self._vars(alert))
        return self._format_alert(alert_record)

    def is_correlated(self, alert):
        select = """
            SELECT * FROM alerts
             WHERE environment=%(environment)s AND resource=%(resource)s
               AND ((event=%(event)s AND severity!=%(severity)s)
                OR (event!=%(event)s AND JSON_CONTAINS(correlate, JSON_QUOTE(%(event)s))))
               AND {customer}
        """.format(customer='customer=%(customer)s' if alert.customer else 'customer IS NULL')
        alert_record = self._fetchone(select, self._vars(alert))
        return self._format_alert(alert_record)

    def is_flapping(self, alert, window=1800, count=2):
        """
        Return true if alert severity has changed more than X times in Y seconds
        """
        select = """
            SELECT COUNT(*) AS count
              FROM alerts a INNER JOIN alert_history h
             WHERE a.environment=%(environment)s
               AND a.resource=%(resource)s
               AND h.event=%(event)s
               AND h.update_time > DATE_SUB(UTC_TIMESTAMP(3) - INTERVAL {window} second)
               AND h.type='severity'
               AND {customer}
        """.format(window=window, customer='customer=%(customer)s' if alert.customer else 'customer IS NULL')
        return self._fetchone(select, self._vars(alert))['count'] > count

    def dedup_alert(self, alert, history):
        """
        Update alert status, service, value, text, timeout and rawData, increment duplicate count and set
        repeat=True, and keep track of last receive id and time but don't append to history unless status changes.
        """
        alert.history = history

        update = """
            UPDATE alerts
               SET status=%(status)s, service=%(service)s, value=%(value)s, text=%(text)s,
                   timeout=%(timeout)s, raw_data=%(raw_data)s, `repeat`=%(repeat)s,
                   last_receive_id=%(last_receive_id)s, last_receive_time=%(last_receive_time)s,
                   tags=(SELECT IFNULL(JSON_ARRAYAGG(tag), '[]') FROM (
                           SELECT DISTINCT t.tag
                           FROM alerts,
                            JSON_TABLE(JSON_MERGE(IFNULL(alerts.tags, '[]'), IFNULL(%(tags)s, '[]')),
                              "$[*]" columns (tag varchar(255) path "$")) t
                        ) as temp),
                   attributes=JSON_MERGE_PATCH(IFNULL(attributes, '{{}}'), %(attributes)s),
                   duplicate_count=duplicate_count + 1, {update_time},
                   history=JSON_EXTRACT(JSON_MERGE(IFNULL(%(history)s, '[]'), history), '$[0 to {limit}]')
             WHERE environment=%(environment)s
               AND resource=%(resource)s
               AND event=%(event)s
               AND severity=%(severity)s
               AND {customer}
        """.format(
            update_time='update_time=%(update_time)s' if alert.update_time else 'update_time=update_time',
            customer='customer=%(customer)s' if alert.customer else 'customer IS NULL',
            limit=current_app.config['HISTORY_LIMIT'] - 1
        )
        self._updateone(update, {
            **self._vars(alert),
            'service': custom_json_dumps(alert.service or []),
            'correlate': custom_json_dumps(alert.correlate or []),
            'tags': custom_json_dumps(alert.tags or []),
            'attributes': custom_json_dumps(alert.attributes or {}),
            'history': alert.history and custom_json_dumps(alert.history.serialize),
            'raw_data': custom_json_dumps(alert.raw_data or {})
        })

        select = """
            SELECT * FROM alerts
             WHERE environment=%(environment)s
               AND resource=%(resource)s
               AND event=%(event)s
               AND severity=%(severity)s
               AND {customer}
        """.format(customer='customer=%(customer)s' if alert.customer else 'customer IS NULL')

        alert_record = self._fetchone(select, self._vars(alert))

        return self._format_alert(alert_record)

    def correlate_alert(self, alert, history):
        alert.history = history
        select = """
            SELECT id FROM alerts
             WHERE environment=%(environment)s
               AND resource=%(resource)s
               AND ((event=%(event)s AND severity!=%(severity)s) OR (event!=%(event)s AND
                JSON_CONTAINS(correlate, JSON_QUOTE(%(event)s))))
               AND {customer}
        """.format(customer='customer=%(customer)s' if alert.customer else 'customer IS NULL')
        alert_id = self._fetchone(select, self._vars(alert))['id']

        update = """
            UPDATE alerts
               SET event=%(event)s, severity=%(severity)s, status=%(status)s, service=%(service)s, value=%(value)s,
                   text=%(text)s, create_time=%(create_time)s, timeout=%(timeout)s, raw_data=%(raw_data)s,
                   duplicate_count=%(duplicate_count)s, `repeat`=%(repeat)s, previous_severity=%(previous_severity)s,
                   trend_indication=%(trend_indication)s, receive_time=%(receive_time)s, last_receive_id=%(last_receive_id)s,
                   last_receive_time=%(last_receive_time)s, tags=({distinct_tags}),
                   attributes=JSON_MERGE_PATCH(IFNULL(attributes, '{{}}'), %(attributes)s), {update_time},
                   history=JSON_EXTRACT(JSON_MERGE(IFNULL(%(history)s, '[]'), history), '$[0 to {limit}]')
             WHERE environment=%(environment)s
               AND resource=%(resource)s
               AND ((event=%(event)s AND severity!=%(severity)s) OR (event!=%(event)s AND
                JSON_CONTAINS(correlate, JSON_QUOTE(%(event)s))))
               AND {customer}
        """.format(
            limit=current_app.config['HISTORY_LIMIT'] - 1,
            update_time='update_time=%(update_time)s' if alert.update_time else 'update_time=update_time',
            customer='customer=%(customer)s' if alert.customer else 'customer IS NULL',
            distinct_tags=self._distinct_tag_query()
        )
        self._updateone(update, {
            **self._vars(alert),
            'service': custom_json_dumps(alert.service or []),
            'tags': custom_json_dumps(alert.tags or []),
            'attributes': custom_json_dumps(alert.attributes or {}),
            'history': custom_json_dumps(list(map(lambda h: h.serialize, alert.history))),
            'raw_data': custom_json_dumps(alert.raw_data or {})
        })

        return self._get_alert_by_id({'id': alert_id, 'like_id': alert_id})

    def create_alert(self, alert):
        insert = """
            INSERT INTO alerts (id, resource, event, environment, severity, correlate, status, service, `group`,
                value, text, tags, attributes, origin, type, create_time, timeout, raw_data, customer,
                duplicate_count, `repeat`, previous_severity, trend_indication, receive_time, last_receive_id,
                last_receive_time, update_time, history)
            VALUES (%(id)s, %(resource)s, %(event)s, %(environment)s, %(severity)s, %(correlate)s, %(status)s,
                %(service)s, %(group)s, %(value)s, %(text)s, %(tags)s, %(attributes)s, %(origin)s,
                %(event_type)s, %(create_time)s, %(timeout)s, %(raw_data)s, %(customer)s, %(duplicate_count)s,
                %(repeat)s, %(previous_severity)s, %(trend_indication)s, %(receive_time)s, %(last_receive_id)s,
                %(last_receive_time)s, %(update_time)s, %(history)s)
        """

        self._insert(insert, {
            **self._vars(alert),
            'history': custom_json_dumps(list(map(lambda h: h.serialize, alert.history))),
            'raw_data': custom_json_dumps(alert.raw_data or {})
        })

        select = """
            SELECT * FROM alerts
             WHERE id=%(id)s
        """
        record = self._fetchone(select, {'id': alert.id})
        return self._format_alert(record)

    def set_alert(self, id, severity, status, tags, attributes, timeout, previous_severity, update_time, history=None):
        update = """
            UPDATE alerts
               SET severity=%(severity)s, status=%(status)s, tags=({distinct_tags}),
                   attributes=%(attributes)s, timeout=%(timeout)s, previous_severity=%(previous_severity)s,
                   update_time=%(update_time)s,
                   history=JSON_MERGE(IFNULL(%(change)s, '[]'), JSON_EXTRACT(history, '$[0 to {limit}]'))
             WHERE id=%(id)s OR id LIKE %(like_id)s
        """.format(limit=current_app.config['HISTORY_LIMIT'] - 1, distinct_tags=self._distinct_tag_query())

        self._updateone(update, {'id': id, 'like_id': id + '%', 'severity': severity, 'status': status,
                                 'tags': custom_json_dumps(tags), 'attributes': custom_json_dumps(attributes),
                                 'timeout': timeout, 'previous_severity': previous_severity,
                                 'update_time': update_time,
                                 'change': custom_json_dumps(list(map(lambda h: h.serialize, history)))})
        return self._get_alert_by_id({'id': id, 'like_id': id + '%'})

    def get_alert(self, id, customers=None):
        select = """
            SELECT * FROM alerts
             WHERE (id REGEXP (%(id)s) OR last_receive_id REGEXP (%(id)s))
               AND {customer}
        """.format(customer='customer=ANY(%(customers)s)' if customers else '1=1')
        return self._format_alert(self._fetchone(select, {'id': '^' + id, 'customers': customers}))

    # STATUS, TAGS, ATTRIBUTES

    def set_status(self, id, status, timeout, update_time, history=None):
        update = """
            UPDATE alerts
            SET status=%(status)s, timeout=%(timeout)s, update_time=%(update_time)s,
            history=JSON_EXTRACT(JSON_MERGE(IFNULL(%(change)s, '[]'), history), '$[0 to {limit}]')
            WHERE id=%(id)s OR id LIKE %(like_id)s
        """.format(limit=current_app.config['HISTORY_LIMIT'] - 1)

        args = {'id': id, 'like_id': id + '%',
                'status': status, 'timeout': timeout, 'update_time': update_time,
                'change': history and custom_json_dumps(history.serialize)}
        self._updateone(update, args)

        return self._get_alert_by_id(args)

    def tag_alert(self, id, tags):
        update = """
            UPDATE alerts
            SET tags=({update_tag})
            WHERE id=%(id)s OR id LIKE %(like_id)s
        """.format(update_tag=self._distinct_tag_query())

        args = {'id': id, 'like_id': id + '%', 'tags': custom_json_dumps(tags)}
        self._updateone(update, args)

        return self._get_alert_by_id(args)

    def untag_alert(self, id, tags):
        update = """
            UPDATE alerts
            SET tags=(
                SELECT IFNULL(json_arrayagg(t.tag), '[]')
                FROM json_table(alerts.tags, "$[*]" columns (tag varchar(255) PATH "$")) t
                WHERE NOT json_contains(%(tags)s, json_quote(t.tag))
            )
            WHERE id=%(id)s OR id LIKE %(like_id)s
        """

        args = {'id': id, 'like_id': id + '%', 'tags': custom_json_dumps(tags)}
        self._updateone(update, args)

        return self._get_alert_by_id(args)

    def update_tags(self, id, tags):
        update = """
            UPDATE alerts
            SET tags=%(tags)s
            WHERE id=%(id)s OR id LIKE %(like_id)s
        """

        args = {'id': id, 'like_id': id + '%', 'tags': custom_json_dumps(tags)}
        self._updateone(update, args)

        return self._get_alert_by_id(args)

    def update_attributes(self, id, old_attrs, new_attrs):
        old_attrs.update(new_attrs)
        attrs = {k: v for k, v in old_attrs.items() if v is not None}

        update = """
            UPDATE alerts
            SET attributes=%(attrs)s
            WHERE id=%(id)s OR id LIKE %(like_id)s
        """
        self._updateone(update, {'id': id, 'like_id': id + '%', 'attrs': custom_json_dumps(attrs)})
        return attrs

    def delete_alert(self, id):
        args = {'id': id, 'like_id': id + '%'}

        select = """
            SELECT id from alerts
            WHERE id=%(id)s OR id LIKE %(like_id)s
        """
        alert_id = self._fetchone(select, args)['id']

        delete = """
            DELETE FROM alerts
            WHERE id=%(id)s OR id LIKE %(like_id)s
        """

        self._deleteone(delete, args)

        return alert_id

    # BULK

    def tag_alerts(self, query=None, tags=None):
        query = query or Query()
        select = f"""
            SELECT id FROM alerts
             WHERE {query.where}
        """
        alert_ids = self._fetchall(select, {**query.vars})

        update = f"""
            UPDATE alerts
            SET tags=({self._distinct_tag_query('_tag')})
            WHERE {query.where}
        """
        self._updateall(update, {**query.vars, '_tags': tags})

        return alert_ids

    def untag_alerts(self, query=None, tags=None):
        query = query or Query()
        select = f"""
            SELECT id FROM alerts
             WHERE {query.where}
        """
        alert_ids = self._fetchall(select, {**query.vars})

        update = """
            UPDATE alerts
            SET tags=(
                SELECT json_arrayagg(t.tag)
                FROM json_table(alerts.tags, "$[*]" columns (tag varchar(255) PATH "$")) t
                WHERE NOT json_contains(%(tags)s, json_quote(t.tag))
            )
            WHERE {where}
        """.format(where=query.where)
        self._updateall(update, {**query.vars, **{'_tags': json.dumps(tags)}})

        return alert_ids

    def update_attributes_by_query(self, query=None, attributes=None):
        query = query or Query()
        select = f"""
            SELECT id FROM alerts
             WHERE {query.where}
        """
        alert_ids = self._fetchall(select, {**query.vars})

        update = f"""
            UPDATE alerts
            SET attributes=JSON_MERGE_PATCH(attributes, %(_attributes)s)
            WHERE {query.where}
        """
        self._updateall(update, {**query.vars, **{'_attributes': json.dumps(attributes or {})}})
        return alert_ids

    def delete_alerts(self, query=None):
        query = query or Query()
        select = f"""
            SELECT id FROM alerts
             WHERE {query.where}
        """
        alert_ids = self._fetchall(select, {**query.vars})

        delete = f"""
            DELETE FROM alerts
            WHERE {query.where}
        """
        self._deleteall(delete, query.vars)
        return alert_ids

    # SEARCH & HISTORY

    def _get_history_columns(self):
        return """
            id            varchar(255)    path "$.id",
            event         varchar(255)    path "$.event",
            severity      varchar(255)    path "$.severity",
            status        varchar(255)    path "$.status",
            value         varchar(255)    path "$.value",
            text          varchar(10000)  path "$.text",
            type          varchar(255)    path "$.type",
            update_time   timestamp       path "$.updateTime",
            user          varchar(255)    path "$.user",
            timeout       integer         path "$.timeout"
        """

    def add_history(self, id, history):
        update = """
            UPDATE alerts
               SET history=(JSON_EXTRACT(JSON_MERGE(%(history)s, history), '$[0 to {limit}]'))
             WHERE id=%(id)s OR id LIKE %(like_id)s
        """.format(limit=current_app.config['HISTORY_LIMIT'] - 1)
        args = {'id': id, 'like_id': id + '%', 'history': custom_json_dumps(history.serialize or [])}
        self._updateone(update, args)

        select = """
            SELECT * FROM alerts
             WHERE id=%(id)s or id LIKE %(like_id)s
        """
        return self._format_alert(self._fetchone(select, args))

    def get_alerts(self, query=None, raw_data=False, history=False, page=None, page_size=None):
        query = query or Query()

        if raw_data and history:
            select = '*'
        else:
            select = (
                'id, resource, event, environment, severity, correlate, status, service, `group`, value, `text`,'
                + 'tags, attributes, origin, type, create_time, timeout, {raw_data}, customer, duplicate_count, `repeat`,'
                + 'previous_severity, trend_indication, receive_time, last_receive_id, last_receive_time, update_time,'
                + '{history}'
            ).format(
                raw_data='raw_data' if raw_data else 'NULL as raw_data',
                history='history' if history else 'CAST("[]" AS JSON) as history'
            )
        join = ''
        if 's.code' in query.sort:
            join += 'JOIN (VALUES {}) AS s(sev, code) ON alerts.severity = s.sev '.format(
                ', '.join((f"('{k}', {v})" for k, v in alarm_model.Severity.items()))
            )
        if 'st.state' in query.sort:
            join += 'JOIN (VALUES {}) AS st(sts, state) ON alerts.status = st.sts '.format(
                ', '.join((f"('{k}', '{v}')" for k, v in alarm_model.Status.items()))
            )
        select = f"""
            SELECT {select}
              FROM alerts {join}
             WHERE {query.where}
          ORDER BY {query.sort or 'last_receive_time'}
        """

        rows = self._fetchall(select, query.vars, limit=page_size, offset=(page - 1) * page_size)
        return [self._format_alert(row) for row in rows]

    def get_alert_history(self, alert, page=None, page_size=None):
        select = """
            SELECT resource, environment, service, `group`, tags, attributes, origin, customer, h.*
              FROM alerts,
                   JSON_TABLE(JSON_EXTRACT(alerts.history, "$[0 to {limit}]"),
                     "$[*]" COLUMNS ({history_columns})
                   ) h
             WHERE environment=%(environment)s AND resource=%(resource)s
               AND (h.event=%(event)s OR JSON_CONTAINS(correlate, JSON_QUOTE(%(event)s)))
               AND {customer}
            ORDER BY update_time DESC
        """.format(
            customer='customer=%(customer)s' if alert.customer else 'customer IS NULL',
            limit=current_app.config['HISTORY_LIMIT'] - 1,
            history_columns=self._get_history_columns()
        )

        return [
            Record(
                id=h['id'],
                resource=h['resource'],
                event=h['event'],
                environment=h['environment'],
                severity=h['severity'],
                status=h['status'],
                service=json.loads(h['service']),
                group=h['group'],
                value=h['value'],
                text=h['text'],
                tags=json.loads(h['tags']),
                attributes=json.loads(h['attributes']),
                origin=h['origin'],
                update_time=h['update_time'],
                user=h.get('user', None),
                timeout=h.get('timeout', None),
                type=h['type'],
                customer=h['customer']
            ) for h in self._fetchall(select, self._vars(alert), limit=page_size, offset=(page - 1) * page_size)
        ]

    def get_history(self, query=None, page=None, page_size=None):
        query = query or Query()
        if 'id' in query.vars:
            select = """
                SELECT a.id
                  FROM alerts a,
                       JSON_TABLE(
                           JSON_EXTRACT(alerts.history, '$[0 to {limit}]'),
                           "$[*]" COLUMNS ({history_columns})
                       ) h
                 WHERE h.id LIKE %(id)s
            """.format(
                limit=current_app.config['HISTORY_LIMIT'] - 1,
                history_columns=self._get_history_columns()
            )
            query.vars['id'] = self._fetchone(select, query.vars)

        select = """
            SELECT resource, environment, service, `group`, tags, attributes, origin, customer, history, h.*
              FROM alerts,
                   JSON_TABLE(
                       JSON_EXTRACT(alerts.history, '$[0 to {limit}]'),
                       "$[*]" COLUMNS ({history_columns})
                   ) h
             WHERE {where}
          ORDER BY update_time DESC
        """.format(
            where=query.where, limit=current_app.config['HISTORY_LIMIT'] - 1,
            history_columns=self._get_history_columns()
        )

        return [
            Record(
                id=h['id'],
                resource=h['resource'],
                event=h['event'],
                environment=h['environment'],
                severity=h['severity'],
                status=h['status'],
                service=json.loads(h['service']),
                group=h['group'],
                value=h['value'],
                text=h['text'],
                tags=json.loads(h['tags']),
                attributes=json.loads(h['attributes']),
                origin=h['origin'],
                update_time=h['update_time'],
                user=h.get('user', None),
                timeout=h.get('timeout', None),
                type=h['type'],
                customer=h['customer']
            ) for h in self._fetchall(select, query.vars, limit=page_size, offset=(page - 1) * page_size)
        ]

    # COUNTS

    def get_count(self, query=None):
        query = query or Query()
        select = f"""
            SELECT COUNT(1) AS count FROM alerts
             WHERE {query.where}
        """
        return self._fetchone(select, query.vars)['count']

    def get_counts(self, query=None, group=None):
        query = query or Query()
        if group is None:
            raise ValueError('Must define a group')
        select = """
            SELECT {group}, COUNT(*) AS count FROM alerts
             WHERE {where}
            GROUP BY {group}
        """.format(where=query.where, group=group)
        return {s['group']: s['count'] for s in self._fetchall(select, query.vars)}

    def get_counts_by_severity(self, query=None):
        query = query or Query()
        select = f"""
            SELECT severity, COUNT(*) AS count FROM alerts
             WHERE {query.where}
            GROUP BY severity
        """
        return {s['severity']: s['count'] for s in self._fetchall(select, query.vars)}

    def get_counts_by_status(self, query=None):
        query = query or Query()
        select = f"""
            SELECT status, COUNT(*) AS count FROM alerts
            WHERE {query.where}
            GROUP BY status
        """
        return {s['status']: s['count'] for s in self._fetchall(select, query.vars)}

    def get_topn_count(self, query=None, group='event', topn=100):
        query = query or Query()
        select = """
            SELECT event,
                   COUNT(1) as count,
                   SUM(duplicate_count) AS duplicate_count,
                   concat('[', group_concat(distinct json_quote(environment)), ']')  AS environments,
                   concat('[', group_concat(distinct json_quote(svc)), ']')          AS services,
                   concat('[', group_concat(distinct json_array(id, resource)), ']') AS resources
              FROM alerts, json_table(alerts.service, "$[*]" columns(svc varchar(500) path "$")) s
             WHERE {where}
          GROUP BY {group}
          ORDER BY count DESC
        """.format(where=query.where, group=group)
        return [
            {
                'count': t['count'],
                'duplicateCount': t['duplicate_count'],
                'environments': json.loads(t['environments'] or '[]'),
                'services': json.loads(t['services'] or '[]'),
                f'{group}': t['event'],
                'resources': [{
                    'id': r[0],
                    'resource': r[1],
                    'href': absolute_url(f'/alert/{r[0]}')
                } for r in json.loads(t['resources'] or '[]')]
            } for t in self._fetchall(select, query.vars, limit=topn)
        ]

    def get_topn_flapping(self, query=None, group='event', topn=100):
        query = query or Query()
        select = """
            WITH topn AS (SELECT * FROM alerts WHERE {where})
            SELECT topn.event,
                   COUNT(1) as count,
                   SUM(duplicate_count) AS duplicate_count,
                   concat('[', group_concat(distinct json_quote(environment)), ']')  AS environments,
                   concat('[', group_concat(distinct json_quote(svc)), ']')          AS services,
                   concat('[', group_concat(distinct json_array(topn.id, resource)), ']') AS resources
              FROM topn,
                   json_table(cast(topn.service as json), '$[*]' columns(svc  varchar(500) path '$')) s,
                   json_table(cast(topn.history as json), '$[*]' columns(type varchar(500) path '$.type')) hist
             WHERE hist.type='severity'
          GROUP BY topn.{group}
          ORDER BY count DESC
        """.format(where=query.where, group=group)
        return [
            {
                'count': t['count'],
                'duplicateCount': t['duplicate_count'],
                'environments': json.loads(t['environments'] or '[]'),
                'services': json.loads(t['services'] or '[]'),
                f'{group}': t['event'],
                'resources': [{
                    'id': r[0],
                    'resource': r[1],
                    'href': absolute_url(f'/alert/{r[0]}')
                } for r in json.loads(t['resources'] or '[]')]
            } for t in self._fetchall(select, query.vars, limit=topn)
        ]

    def get_topn_standing(self, query=None, group='event', topn=100):
        query = query or Query()
        select = """
            WITH topn AS (SELECT * FROM alerts WHERE {where})
            SELECT topn.event,
                   COUNT(1) as count,
                   SUM(duplicate_count) AS duplicate_count,
                   SUM(last_receive_time - create_time) as life_time,
                   concat('[', group_concat(distinct json_quote(environment)), ']')  AS environments,
                   concat('[', group_concat(distinct json_quote(svc)), ']')          AS services,
                   concat('[', group_concat(distinct json_array(topn.id, resource)), ']') AS resources
              FROM topn,
                   json_table(cast(topn.service as json), '$[*]' columns(svc  varchar(500) path '$')) s,
                   json_table(cast(topn.history as json), '$[*]' columns(type varchar(500) path '$.type')) hist
             WHERE hist.type='severity'
          GROUP BY topn.{group}
          ORDER BY life_time DESC
        """.format(where=query.where, group=group)
        return [
            {
                'count': t['count'],
                'duplicateCount': t['duplicate_count'],
                'environments': json.loads(t['environments'] or '[]'),
                'services': json.loads(t['services'] or '[]'),
                f'{group}': t['event'],
                'resources': [{
                    'id': r[0],
                    'resource': r[1],
                    'href': absolute_url(f'/alert/{r[0]}')
                } for r in json.loads(t['resources'] or '[]')]
            } for t in self._fetchall(select, query.vars, limit=topn)
        ]

    # ENVIRONMENTS

    def get_environments(self, query=None, topn=1000):
        query = query or Query()

        def pipeline(group_by):
            select = f"""
                SELECT environment, {group_by}, count(1) AS count FROM alerts
                WHERE {query.where}
                GROUP BY environment, {group_by}
            """
            return self._fetchall(select, query.vars, limit=topn)

        severity_count = defaultdict(list)
        status_count = defaultdict(list)

        result = pipeline('severity')
        for row in result:
            severity_count[row['environment']].append((row['severity'], row['count']))

        result = pipeline('status')
        for row in result:
            status_count[row['environment']].append((row['status'], row['count']))

        select = """SELECT DISTINCT environment FROM alerts"""
        environments = self._fetchall(select, {})

        return [
            {
                'environment': e['environment'],
                'severityCounts': dict(severity_count[e['environment']]),
                'statusCounts': dict(status_count[e['environment']]),
                'count': sum(t[1] for t in severity_count[e['environment']]),
            } for e in environments]

    # SERVICES

    def get_services(self, query=None, topn=1000):
        query = query or Query()

        def pipeline(group_by):
            select = """
                SELECT environment, s.svc, {group_by}, count(1) AS count
                FROM alerts,
                    JSON_TABLE(alerts.service,
                    "$[*]" COLUMNS (svc varchar(500) path "$")
                    ) s
                WHERE {where}
                GROUP BY environment, svc, {group_by}
            """.format(where=query.where, group_by=group_by)
            return self._fetchall(select, query.vars, limit=topn)

        severity_count = defaultdict(list)
        result = pipeline('severity')
        for row in result:
            severity_count[(row['environment'], row['svc'])].append((row['severity'], row['count']))

        status_count = defaultdict(list)
        result = pipeline('status')
        for row in result:
            status_count[(row['environment'], row['svc'])].append((row['status'], row['count']))

        select = """
            SELECT DISTINCT environment, s.svc
            FROM alerts,
                 JSON_TABLE(alerts.service,
                    "$[*]" COLUMNS (svc varchar(500) path "$")
                 ) s
        """
        services = self._fetchall(select, {})
        return [
            {
                'environment': s['environment'],
                'service': s['svc'],
                'severityCounts': dict(severity_count[(s['environment'], s['svc'])]),
                'statusCounts': dict(status_count[(s['environment'], s['svc'])]),
                'count': sum(t[1] for t in severity_count[(s['environment'], s['svc'])])
            } for s in services]

    # ALERT GROUPS

    def get_alert_groups(self, query=None, topn=1000):
        query = query or Query()
        select = f"""
            SELECT environment, `group` COLLATE utf8_bin as `group`, count(1) AS count FROM alerts
            WHERE {query.where}
            GROUP BY environment, `group` COLLATE utf8_bin
        """
        return self._fetchall(select, query.vars, limit=topn)

    # ALERT TAGS

    def get_alert_tags(self, query=None, topn=1000):
        query = query or Query()
        select = """
            SELECT environment, t.tag as tag, count(1) AS count FROM alerts,
                JSON_TABLE(alerts.tags, "$[*]" COLUMNS (tag varchar(255) path "$")) t
            WHERE {where}
            GROUP BY environment, t.tag
        """.format(where=query.where)
        return self._fetchall(select, query.vars, limit=topn)

    # BLACKOUTS

    def _format_blackout(self, blackout):
        if blackout:
            row = {
                **blackout,
                'service': json.loads(blackout['service']),
                'tags': json.loads(blackout['tags'])
            }
            named_tuple = namedtuple('blackout', row.keys())
            return named_tuple(*row.values())

    def create_blackout(self, blackout):
        insert = """
            INSERT INTO blackouts (id, priority, environment, service, resource, event,
                `group`, tags, origin, customer, start_time, end_time,
                duration, `user`, create_time, text)
            VALUES (%(id)s, %(priority)s, %(environment)s, %(service)s, %(resource)s, %(event)s,
                %(group)s, %(tags)s, %(origin)s, %(customer)s, %(start_time)s, %(end_time)s,
                %(duration)s, %(user)s, %(create_time)s, %(text)s)
        """
        self._insert(insert, {
            **self._vars(blackout),
            'service': json.dumps(blackout.service or []),
            'tags': json.dumps(blackout.tags or [])
        })

        select = """
            SELECT *, duration as remaining FROM blackouts
             WHERE id=%(id)s
        """
        return self._format_blackout(self._fetchone(select, self._vars(blackout)))

    def get_blackout(self, id, customers=None):
        select = """
            SELECT *, GREATEST(UNIX_TIMESTAMP(end_time - GREATEST(start_time, UTC_TIMESTAMP(3))), 0) AS remaining
            FROM blackouts
            WHERE id=%(id)s
              AND {customer}
        """.format(customer='JSON_CONTAINS(%(customers)s, customer)' if customers else '1=1')
        args = {'id': id, 'customers': json.dumps(customers or [])}
        return self._format_blackout(self._fetchone(select, args))

    def get_blackouts(self, query=None, page=None, page_size=None):
        query = query or Query()
        select = """
            SELECT *, GREATEST(UNIX_TIMESTAMP(end_time - GREATEST(start_time, UTC_TIMESTAMP(3))), 0) AS remaining
              FROM blackouts
             WHERE {where}
          ORDER BY {order}
        """.format(where=query.where, order=query.sort)
        blackouts = self._fetchall(select, query.vars, limit=page_size, offset=(page - 1) * page_size)
        return [self._format_blackout(b) for b in blackouts]

    def get_blackouts_count(self, query=None):
        query = query or Query()
        select = f"""
            SELECT COUNT(1) AS count FROM blackouts
             WHERE {query.where}
        """
        return self._fetchone(select, query.vars)['count']

    def is_blackout_period(self, alert):
        select = """
            SELECT *
            FROM blackouts
            WHERE start_time <= %(create_time)s AND end_time > %(create_time)s
              AND environment=%(environment)s
              AND (
                 ( resource IS NULL AND JSON_LENGTH(service)=0 AND event IS NULL AND `group` IS NULL AND JSON_LENGTH(tags)=0 AND origin IS NULL )
              OR ( resource IS NULL AND JSON_LENGTH(service)=0 AND event IS NULL AND `group` IS NULL AND JSON_LENGTH(tags)=0 AND origin=%(origin)s )
              OR ( resource IS NULL AND JSON_LENGTH(service)=0 AND event IS NULL AND `group` IS NULL AND JSON_CONTAINS(%(tags)s, tags) AND origin IS NULL )
              OR ( resource IS NULL AND JSON_LENGTH(service)=0 AND event IS NULL AND `group` IS NULL AND JSON_CONTAINS(%(tags)s, tags) AND origin=%(origin)s )
              OR ( resource IS NULL AND JSON_LENGTH(service)=0 AND event IS NULL AND `group`=%(group)s AND JSON_LENGTH(tags)=0 AND origin IS NULL )
              OR ( resource IS NULL AND JSON_LENGTH(service)=0 AND event IS NULL AND `group`=%(group)s AND JSON_LENGTH(tags)=0 AND origin=%(origin)s )
              OR ( resource IS NULL AND JSON_LENGTH(service)=0 AND event IS NULL AND `group`=%(group)s AND JSON_CONTAINS(%(tags)s, tags) AND origin IS NULL )
              OR ( resource IS NULL AND JSON_LENGTH(service)=0 AND event IS NULL AND `group`=%(group)s AND JSON_CONTAINS(%(tags)s, tags) AND origin=%(origin)s )
              OR ( resource IS NULL AND JSON_LENGTH(service)=0 AND event=%(event)s AND `group` IS NULL AND JSON_LENGTH(tags)=0 AND origin IS NULL )
              OR ( resource IS NULL AND JSON_LENGTH(service)=0 AND event=%(event)s AND `group` IS NULL AND JSON_LENGTH(tags)=0 AND origin=%(origin)s )
              OR ( resource IS NULL AND JSON_LENGTH(service)=0 AND event=%(event)s AND `group` IS NULL AND JSON_CONTAINS(%(tags)s, tags) AND origin IS NULL )
              OR ( resource IS NULL AND JSON_LENGTH(service)=0 AND event=%(event)s AND `group` IS NULL AND JSON_CONTAINS(%(tags)s, tags) AND origin=%(origin)s )
              OR ( resource IS NULL AND JSON_LENGTH(service)=0 AND event=%(event)s AND `group`=%(group)s AND JSON_LENGTH(tags)=0 AND origin IS NULL )
              OR ( resource IS NULL AND JSON_LENGTH(service)=0 AND event=%(event)s AND `group`=%(group)s AND JSON_LENGTH(tags)=0 AND origin=%(origin)s )
              OR ( resource IS NULL AND JSON_LENGTH(service)=0 AND event=%(event)s AND `group`=%(group)s AND JSON_CONTAINS(%(tags)s, tags) AND origin IS NULL )
              OR ( resource IS NULL AND JSON_LENGTH(service)=0 AND event=%(event)s AND `group`=%(group)s AND JSON_CONTAINS(%(tags)s, tags) AND origin=%(origin)s )
              OR ( resource IS NULL AND JSON_CONTAINS(%(service)s, service) AND event IS NULL AND `group` IS NULL AND JSON_LENGTH(tags)=0 AND origin IS NULL )
              OR ( resource IS NULL AND JSON_CONTAINS(%(service)s, service) AND event IS NULL AND `group` IS NULL AND JSON_LENGTH(tags)=0 AND origin=%(origin)s )
              OR ( resource IS NULL AND JSON_CONTAINS(%(service)s, service) AND event IS NULL AND `group` IS NULL AND JSON_CONTAINS(%(tags)s, tags) AND origin IS NULL )
              OR ( resource IS NULL AND JSON_CONTAINS(%(service)s, service) AND event IS NULL AND `group` IS NULL AND JSON_CONTAINS(%(tags)s, tags) AND origin=%(origin)s )
              OR ( resource IS NULL AND JSON_CONTAINS(%(service)s, service) AND event IS NULL AND `group`=%(group)s AND JSON_LENGTH(tags)=0 AND origin IS NULL )
              OR ( resource IS NULL AND JSON_CONTAINS(%(service)s, service) AND event IS NULL AND `group`=%(group)s AND JSON_LENGTH(tags)=0 AND origin=%(origin)s )
              OR ( resource IS NULL AND JSON_CONTAINS(%(service)s, service) AND event IS NULL AND `group`=%(group)s AND JSON_CONTAINS(%(tags)s, tags) AND origin IS NULL )
              OR ( resource IS NULL AND JSON_CONTAINS(%(service)s, service) AND event IS NULL AND `group`=%(group)s AND JSON_CONTAINS(%(tags)s, tags) AND origin=%(origin)s )
              OR ( resource IS NULL AND JSON_CONTAINS(%(service)s, service) AND event=%(event)s AND `group` IS NULL AND JSON_LENGTH(tags)=0 AND origin IS NULL )
              OR ( resource IS NULL AND JSON_CONTAINS(%(service)s, service) AND event=%(event)s AND `group` IS NULL AND JSON_LENGTH(tags)=0 AND origin=%(origin)s )
              OR ( resource IS NULL AND JSON_CONTAINS(%(service)s, service) AND event=%(event)s AND `group` IS NULL AND JSON_CONTAINS(%(tags)s, tags) AND origin IS NULL )
              OR ( resource IS NULL AND JSON_CONTAINS(%(service)s, service) AND event=%(event)s AND `group` IS NULL AND JSON_CONTAINS(%(tags)s, tags) AND origin=%(origin)s )
              OR ( resource IS NULL AND JSON_CONTAINS(%(service)s, service) AND event=%(event)s AND `group`=%(group)s AND JSON_LENGTH(tags)=0 AND origin IS NULL )
              OR ( resource IS NULL AND JSON_CONTAINS(%(service)s, service) AND event=%(event)s AND `group`=%(group)s AND JSON_LENGTH(tags)=0 AND origin=%(origin)s )
              OR ( resource IS NULL AND JSON_CONTAINS(%(service)s, service) AND event=%(event)s AND `group`=%(group)s AND JSON_CONTAINS(%(tags)s, tags) AND origin IS NULL )
              OR ( resource IS NULL AND JSON_CONTAINS(%(service)s, service) AND event=%(event)s AND `group`=%(group)s AND JSON_CONTAINS(%(tags)s, tags) AND origin=%(origin)s )
              OR ( resource=%(resource)s AND JSON_LENGTH(service)=0 AND event IS NULL AND `group` IS NULL AND JSON_LENGTH(tags)=0 AND origin IS NULL )
              OR ( resource=%(resource)s AND JSON_LENGTH(service)=0 AND event IS NULL AND `group` IS NULL AND JSON_LENGTH(tags)=0 AND origin=%(origin)s )
              OR ( resource=%(resource)s AND JSON_LENGTH(service)=0 AND event IS NULL AND `group` IS NULL AND JSON_CONTAINS(%(tags)s, tags) AND origin IS NULL )
              OR ( resource=%(resource)s AND JSON_LENGTH(service)=0 AND event IS NULL AND `group` IS NULL AND JSON_CONTAINS(%(tags)s, tags) AND origin=%(origin)s )
              OR ( resource=%(resource)s AND JSON_LENGTH(service)=0 AND event IS NULL AND `group`=%(group)s AND JSON_LENGTH(tags)=0 AND origin IS NULL )
              OR ( resource=%(resource)s AND JSON_LENGTH(service)=0 AND event IS NULL AND `group`=%(group)s AND JSON_LENGTH(tags)=0 AND origin=%(origin)s )
              OR ( resource=%(resource)s AND JSON_LENGTH(service)=0 AND event IS NULL AND `group`=%(group)s AND JSON_CONTAINS(%(tags)s, tags) AND origin IS NULL )
              OR ( resource=%(resource)s AND JSON_LENGTH(service)=0 AND event IS NULL AND `group`=%(group)s AND JSON_CONTAINS(%(tags)s, tags) AND origin=%(origin)s )
              OR ( resource=%(resource)s AND JSON_LENGTH(service)=0 AND event=%(event)s AND `group` IS NULL AND JSON_LENGTH(tags)=0 AND origin IS NULL )
              OR ( resource=%(resource)s AND JSON_LENGTH(service)=0 AND event=%(event)s AND `group` IS NULL AND JSON_LENGTH(tags)=0 AND origin=%(origin)s )
              OR ( resource=%(resource)s AND JSON_LENGTH(service)=0 AND event=%(event)s AND `group` IS NULL AND JSON_CONTAINS(%(tags)s, tags) AND origin IS NULL )
              OR ( resource=%(resource)s AND JSON_LENGTH(service)=0 AND event=%(event)s AND `group` IS NULL AND JSON_CONTAINS(%(tags)s, tags) AND origin=%(origin)s )
              OR ( resource=%(resource)s AND JSON_LENGTH(service)=0 AND event=%(event)s AND `group`=%(group)s AND JSON_LENGTH(tags)=0 AND origin IS NULL )
              OR ( resource=%(resource)s AND JSON_LENGTH(service)=0 AND event=%(event)s AND `group`=%(group)s AND JSON_LENGTH(tags)=0 AND origin=%(origin)s )
              OR ( resource=%(resource)s AND JSON_LENGTH(service)=0 AND event=%(event)s AND `group`=%(group)s AND JSON_CONTAINS(%(tags)s, tags) AND origin IS NULL )
              OR ( resource=%(resource)s AND JSON_LENGTH(service)=0 AND event=%(event)s AND `group`=%(group)s AND JSON_CONTAINS(%(tags)s, tags) AND origin=%(origin)s )
              OR ( resource=%(resource)s AND JSON_CONTAINS(%(service)s, service) AND event IS NULL AND `group` IS NULL AND JSON_LENGTH(tags)=0 AND origin IS NULL )
              OR ( resource=%(resource)s AND JSON_CONTAINS(%(service)s, service) AND event IS NULL AND `group` IS NULL AND JSON_LENGTH(tags)=0 AND origin=%(origin)s )
              OR ( resource=%(resource)s AND JSON_CONTAINS(%(service)s, service) AND event IS NULL AND `group` IS NULL AND JSON_CONTAINS(%(tags)s, tags) AND origin IS NULL )
              OR ( resource=%(resource)s AND JSON_CONTAINS(%(service)s, service) AND event IS NULL AND `group` IS NULL AND JSON_CONTAINS(%(tags)s, tags) AND origin=%(origin)s )
              OR ( resource=%(resource)s AND JSON_CONTAINS(%(service)s, service) AND event IS NULL AND `group`=%(group)s AND JSON_LENGTH(tags)=0 AND origin IS NULL )
              OR ( resource=%(resource)s AND JSON_CONTAINS(%(service)s, service) AND event IS NULL AND `group`=%(group)s AND JSON_LENGTH(tags)=0 AND origin=%(origin)s )
              OR ( resource=%(resource)s AND JSON_CONTAINS(%(service)s, service) AND event IS NULL AND `group`=%(group)s AND JSON_CONTAINS(%(tags)s, tags) AND origin IS NULL )
              OR ( resource=%(resource)s AND JSON_CONTAINS(%(service)s, service) AND event IS NULL AND `group`=%(group)s AND JSON_CONTAINS(%(tags)s, tags) AND origin=%(origin)s )
              OR ( resource=%(resource)s AND JSON_CONTAINS(%(service)s, service) AND event=%(event)s AND `group` IS NULL AND JSON_LENGTH(tags)=0 AND origin IS NULL )
              OR ( resource=%(resource)s AND JSON_CONTAINS(%(service)s, service) AND event=%(event)s AND `group` IS NULL AND JSON_LENGTH(tags)=0 AND origin=%(origin)s )
              OR ( resource=%(resource)s AND JSON_CONTAINS(%(service)s, service) AND event=%(event)s AND `group` IS NULL AND JSON_CONTAINS(%(tags)s, tags) AND origin IS NULL )
              OR ( resource=%(resource)s AND JSON_CONTAINS(%(service)s, service) AND event=%(event)s AND `group` IS NULL AND JSON_CONTAINS(%(tags)s, tags) AND origin=%(origin)s )
              OR ( resource=%(resource)s AND JSON_CONTAINS(%(service)s, service) AND event=%(event)s AND `group`=%(group)s AND JSON_LENGTH(tags)=0 AND origin IS NULL )
              OR ( resource=%(resource)s AND JSON_CONTAINS(%(service)s, service) AND event=%(event)s AND `group`=%(group)s AND JSON_LENGTH(tags)=0 AND origin=%(origin)s )
              OR ( resource=%(resource)s AND JSON_CONTAINS(%(service)s, service) AND event=%(event)s AND `group`=%(group)s AND JSON_CONTAINS(%(tags)s, tags) AND origin IS NULL )
              OR ( resource=%(resource)s AND JSON_CONTAINS(%(service)s, service) AND event=%(event)s AND `group`=%(group)s AND JSON_CONTAINS(%(tags)s, tags) AND origin=%(origin)s )
                 )
        """
        if current_app.config['CUSTOMER_VIEWS']:
            select += ' AND (customer IS NULL OR customer=%(customer)s)'

        args = {
            **self._vars(alert),
            'tags': json.dumps(alert.tags or []),
            'service': json.dumps(alert.service or []),
        }
        if self._fetchone(select, args):
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
            kwargs['service'] = json.dumps(kwargs['service'] or [])
        if 'resource' in kwargs:
            update += 'resource=%(resource)s, '
        if 'event' in kwargs:
            update += 'event=%(event)s, '
        if 'group' in kwargs:
            update += '`group`=%(group)s, '
        if 'tags' in kwargs:
            update += 'tags=%(tags)s, '
            kwargs['tags'] = json.dumps(kwargs['tags'] or [])
        if 'origin' in kwargs:
            update += 'origin=%(origin)s, '
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
            `user`=COALESCE(%(user)s, `user`)
            WHERE id=%(id)s
        """
        kwargs['id'] = id
        kwargs['user'] = kwargs.get('user')
        self._updateone(update, kwargs)

        select = """
            SELECT *, GREATEST(UNIX_TIMESTAMP(end_time - GREATEST(start_time, UTC_TIMESTAMP(3))), 0) AS remaining
             FROM blackouts
        """
        blackout = self._fetchone(select, kwargs)
        return self._format_blackout(blackout)

    def delete_blackout(self, id):
        delete = """
            DELETE FROM blackouts
            WHERE id=%(id)s
        """
        self._deleteone(delete, {'id': id})
        return id

    # HEARTBEATS
    def _format_heartbeat(self, heartbeat):
        if heartbeat:
            row = {
                **heartbeat,
                'attributes': json.loads(heartbeat['attributes']),
                'tags': json.loads(heartbeat['tags'])
            }
            named_tuple = namedtuple('heartbeat', row.keys())
            return named_tuple(*row.values())

    def _format_heartbeats(self, heartbeats):
        rows = []
        if heartbeats:
            named_tuple = namedtuple('heartbeat', {**heartbeats[0]}.keys())
            for heartbeat in heartbeats:
                row = {
                    **heartbeat,
                    'attributes': json.loads(heartbeat['attributes']),
                    'tags': json.loads(heartbeat['tags'])
                }
                rows.append(named_tuple(*row.values()))
        return rows

    def upsert_heartbeat(self, heartbeat):
        select = """
            SELECT id FROM heartbeats
            WHERE origin=%(origin)s AND coalesce(customer, '')=%(customer)s
        """
        exists = self._fetchone(select, {
            **self._vars(heartbeat),
            'customer': heartbeat.customer or ''
        })
        if not exists:
            insert = """
                INSERT INTO heartbeats (id, origin, tags, attributes, type, create_time, timeout, receive_time, customer)
                VALUES (%(id)s, %(origin)s, %(tags)s, %(attributes)s, %(event_type)s, %(create_time)s, %(timeout)s, %(receive_time)s, %(customer)s)
            """
            self._insert(insert, {
                **self._vars(heartbeat),
                'tags': json.dumps(heartbeat.tags or []),
                'attributes': json.dumps(heartbeat.attributes or {})
            })
        else:
            update = """
                UPDATE heartbeats
                SET tags=%(tags)s, attributes=%(attributes)s, create_time=%(create_time)s, timeout=%(timeout)s, receive_time=%(receive_time)s
                WHERE id=%(id)s
            """
            self._updateone(update, {
                **self._vars(heartbeat),
                'tags': json.dumps(heartbeat.tags or []),
                'attributes': json.dumps(heartbeat.attributes or {}),
                'id': exists['id']
            })

        select = """
            SELECT *,
                UNIX_TIMESTAMP(receive_time - create_time) AS latency,
                UNIX_TIMESTAMP(NOW() - receive_time) AS since
            FROM heartbeats
            WHERE id=%(id)s
        """
        id = (exists and exists['id']) or heartbeat.id
        return self._format_heartbeat(self._fetchone(select, {'id': id}))

    def get_heartbeat(self, id, customers=None):
        select = """
            SELECT *,
                   UNIX_TIMESTAMP(receive_time - create_time) AS latency,
                   UNIX_TIMESTAMP(NOW() - receive_time) AS since
              FROM heartbeats
             WHERE (id=%(id)s OR id LIKE %(like_id)s)
               AND {customer}
        """.format(customer='customer=%(customers)s' if customers else '1=1')
        return self._format_heartbeat(self._fetchone(select, {'id': id, 'like_id': id + '%', 'customers': customers}))

    def get_heartbeats(self, query=None, page=None, page_size=None):
        query = query or Query()
        select = """
            SELECT *,
                   UNIX_TIMESTAMP(receive_time - create_time) AS latency,
                   UNIX_TIMESTAMP(NOW() - receive_time) AS since
              FROM heartbeats
             WHERE {where}
          ORDER BY {order}
        """.format(where=query.where, order=query.sort)
        heartbeats = self._fetchall(select, query.vars, limit=page_size, offset=(page - 1) * page_size)
        return self._format_heartbeats(heartbeats)

    def get_heartbeats_by_status(self, status=None, query=None, page=None, page_size=None):
        status = status or list()
        query = query or Query()

        swhere = ''
        if status:
            q = list()
            if HeartbeatStatus.OK in status:
                q.append(
                    """
                    (UNIX_TIMESTAMP(UTC_TIMESTAMP(3) - receive_time) <= timeout
                    AND UNIX_TIMESTAMP(receive_time - create_time) * 1000 <= {max_latency})
                    """.format(max_latency=current_app.config['HEARTBEAT_MAX_LATENCY']))
            if HeartbeatStatus.Expired in status:
                q.append('(UNIX_TIMESTAMP(UTC_TIMESTAMP(3) - receive_time) > timeout)')
            if HeartbeatStatus.Slow in status:
                q.append(
                    """
                    (UNIX_TIMESTAMP(UTC_TIMESTAMP(3) - receive_time) <= timeout
                    AND UNIX_TIMESTAMP(receive_time - create_time) * 1000 > {max_latency})
                    """.format(max_latency=current_app.config['HEARTBEAT_MAX_LATENCY']))
            if q:
                swhere = 'AND (' + ' OR '.join(q) + ')'

        select = """
            SELECT *,
                   UNIX_TIMESTAMP(receive_time - create_time) AS latency,
                   UNIX_TIMESTAMP(UTC_TIMESTAMP(3) - receive_time) AS since
              FROM heartbeats
             WHERE {where}
             {swhere}
          ORDER BY {order}
        """.format(where=query.where, swhere=swhere, order=query.sort)
        heartbeats = self._fetchall(select, query.vars, limit=page_size, offset=(page - 1) * page_size)
        return self._format_heartbeats(heartbeats)

    def get_heartbeats_count(self, query=None):
        query = query or Query()
        select = f"""
            SELECT COUNT(1) AS count FROM heartbeats
             WHERE {query.where}
        """
        return self._fetchone(select, query.vars)['count']

    def delete_heartbeat(self, id):
        select = """
            SELECT id FROM heartbeats
            WHERE id=%(id)s OR id LIKE %(like_id)s
        """
        args = {'id': id, 'like_id': id + '%'}

        hb_id = self._fetchone(select, args)
        delete = """
            DELETE FROM heartbeats
            WHERE id=%(id)s OR id LIKE %(like_id)s
        """
        self._deleteone(delete, args)
        return hb_id['id']

    # API KEYS

    def _format_key(self, key):
        if key:
            row = {
                **key,
                'scopes': json.loads(key['scopes'])
            }
            named_tuple = namedtuple('key', row.keys())
            return named_tuple(*row.values())

    def _format_keys(self, keys):
        rows = []
        if keys:
            named_tuple = namedtuple('key', {**keys[0]}.keys())
            for key in keys:
                row = {
                    **key,
                    'scopes': json.loads(key['scopes'])
                }
                rows.append(named_tuple(*row.values()))
        return rows

    def create_key(self, key):
        insert = """
            INSERT INTO `keys` (id, `key`, `user`, scopes, text, expire_time, `count`, last_used_time, customer)
            VALUES (%(id)s, %(key)s, %(user)s, %(scopes)s, %(text)s, %(expire_time)s, %(count)s, %(last_used_time)s, %(customer)s)
        """
        self._insert(insert, {**self._vars(key), 'scopes': json.dumps(key.scopes or [])})

        select = """
            SELECT * from `keys`
             WHERE id=%(id)s
        """
        key = self._fetchone(select, self._vars(key))
        return self._format_key(key)

    def get_key(self, key, user=None):
        select = f"""
            SELECT * FROM `keys`
             WHERE (id=%(key)s OR `key`=%(key)s)
               AND {'`user`=%(user)s' if user else '1=1'}
        """
        return self._format_key(self._fetchone(select, {'key': key, 'user': user}))

    def get_keys(self, query=None, page=None, page_size=None):
        query = query or Query()
        select = f"""
            SELECT * FROM `keys`
             WHERE {query.where}
          ORDER BY {query.sort}
        """
        keys = self._fetchall(select, query.vars, limit=page_size, offset=(page - 1) * page_size)
        return [self._format_key(key) for key in keys]

    def get_keys_by_user(self, user):
        select = """
            SELECT * FROM `keys`
             WHERE `user`=%(user)s
        """
        return self._format_keys(self._fetchall(select, {'user': user}))

    def get_keys_count(self, query=None):
        query = query or Query()
        select = f"""
            SELECT COUNT(1) AS count FROM `keys`
             WHERE {query.where}
        """
        return self._fetchone(select, query.vars)['count']

    def update_key(self, key, **kwargs):
        update = """
            UPDATE `keys`
            SET
        """
        if 'user' in kwargs:
            update += '`user`=%(user)s, '
        if 'scopes' in kwargs:
            update += 'scopes=%(scopes)s, '
            kwargs['scopes'] = json.dumps(kwargs['scopes'] or [])
        if 'text' in kwargs:
            update += 'text=%(text)s, '
        if 'expireTime' in kwargs:
            update += 'expire_time=%(expireTime)s, '
        if 'customer' in kwargs:
            update += 'customer=%(customer)s, '
        update += """
            id=id
            WHERE id=%(key)s OR `key`=%(key)s
        """
        kwargs['key'] = key
        self._updateone(update, kwargs)

        select = """
            SELECT * FROM `keys`
             WHERE id=%(key)s OR `key`=%(key)s
        """
        record = self._fetchone(select, kwargs)
        return self._format_key(record)

    def update_key_last_used(self, key):
        update = """
            UPDATE `keys`
            SET last_used_time=UTC_TIMESTAMP(3), count=count + 1
            WHERE id=%(key)s OR `key`=%(key)s
        """
        self._updateone(update, {'key': key})

    def delete_key(self, key):
        select = """
            SELECT `key` FROM `keys`
             WHERE id=%(key)s or `key`=%(key)s
        """
        deleted_key = self._fetchone(select, {'key': key})['key']

        delete = """
            DELETE FROM `keys`
            WHERE id=%(key)s OR `key`=%(key)s
        """
        self._deleteone(delete, {'key': key})

        return deleted_key

    # USERS

    def _format_user(self, user):
        if user:
            row = {
                **user,
                'roles': json.loads(user['roles']),
                'attributes': json.loads(user['attributes']),
            }
            named_tuple = namedtuple('user', row.keys())
            return named_tuple(*row.values())

    def _format_users(self, users):
        rows = []
        if users:
            named_tuple = namedtuple('user', {**users[0]}.keys())
            for user in users:
                row = {
                    **user,
                    'roles': json.loads(user['roles']),
                    'attributes': json.loads(user['attributes']),
                }
                rows.append(named_tuple(*row.values()))
        return rows

    def create_user(self, user):
        insert = """
            INSERT INTO users (id, name, login, password, email, status, roles, attributes,
                create_time, last_login, text, update_time, email_verified)
            VALUES (%(id)s, %(name)s, %(login)s, %(password)s, %(email)s, %(status)s, %(roles)s, %(attributes)s, %(create_time)s,
                %(last_login)s, %(text)s, %(update_time)s, %(email_verified)s)
        """
        self._insert(insert, {
            **self._vars(user),
            'attributes': json.dumps(user.attributes or {}),
            'roles': json.dumps(user.roles or [])
        })

        select = """
            SELECT * FROM users
             WHERE id=%(id)s
        """
        return self._format_user(self._fetchone(select, self._vars(user)))

    def get_user(self, id):
        select = """SELECT * FROM users WHERE id=%(id)s"""
        return self._format_user(self._fetchone(select, {'id': id}))

    def get_users(self, query=None, page=None, page_size=None):
        query = query or Query()
        select = f"""
            SELECT * FROM users
             WHERE {query.where}
          ORDER BY {query.sort}
        """
        users = self._fetchall(select, query.vars, limit=page_size, offset=(page - 1) * page_size)
        return self._format_users(users)

    def get_users_count(self, query=None):
        query = query or Query()
        select = f"""
            SELECT COUNT(1) AS count FROM users
             WHERE {query.where}
        """
        return self._fetchone(select, query.vars)['count']

    def get_user_by_username(self, username):
        select = """SELECT * FROM users WHERE login=%(login)s OR email=%(login)s"""
        return self._format_user(self._fetchone(select, {'login': username}))

    def get_user_by_email(self, email):
        select = """SELECT * FROM users WHERE email=%(email)s"""
        return self._format_user(self._fetchone(select, {'email': email}))

    def get_user_by_hash(self, hash):
        select = """SELECT * FROM users WHERE hash=%(hash)s"""
        return self._format_user(self._fetchone(select, {'hash': hash}))

    def update_last_login(self, id):
        update = """
            UPDATE users
            SET last_login=UTC_TIMESTAMP(3)
            WHERE id=%(id)s
        """
        self._updateone(update, {'id': id})

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
            kwargs['roles'] = json.dumps(kwargs['roles'] or [])
        if kwargs.get('attributes', None) is not None:
            update += "attributes=JSON_MERGE_PATCH(IFNULL(attributes, '{}'), %(attributes)s), "
            kwargs['attributes'] = json.dumps(kwargs['attributes'] or {})
        if kwargs.get('text', None) is not None:
            update += 'text=%(text)s, '
        if kwargs.get('email_verified', None) is not None:
            update += 'email_verified=%(email_verified)s, '
        update += """
            update_time=UTC_TIMESTAMP(3)
            WHERE id=%(id)s
        """
        kwargs['id'] = id
        self._updateone(update, kwargs)

        select = """
            SELECT * FROM users
             WHERE id=%(id)s
        """
        return self._format_user(self._fetchone(select, kwargs))

    def update_user_attributes(self, id, old_attrs, new_attrs):
        from alerta.utils.collections import merge
        merge(old_attrs, new_attrs)
        attrs = {k: v for k, v in old_attrs.items() if v is not None}
        update = """
            UPDATE users
               SET attributes=%(attrs)s, update_time=UTC_TIMESTAMP(3)
             WHERE id=%(id)s
        """
        self._updateone(update, {'id': id, 'attrs': json.dumps(attrs)})
        return bool(id)

    def delete_user(self, id):
        delete = """
            DELETE FROM users
            WHERE id=%(id)s
        """
        self._deleteone(delete, {'id': id})
        return id

    def set_email_hash(self, id, hash):
        update = """
            UPDATE users
            SET hash=%(hash)s, update_time=UTC_TIMESTAMP(3)
            WHERE id=%(id)s
        """
        self._updateone(update, {'id': id, 'hash': hash})

    # GROUPS

    def _format_group(self, group):
        if group:
            row = {
                **group,
                'users': json.loads(group['users'] or '[]'),
                'tags': json.loads(group['tags'] or '[]'),
                'attributes': json.loads(group['attributes'] or '{}'),
            }
            named_tuple = namedtuple('group', row.keys())
            return named_tuple(*row.values())

    def _format_groups(self, groups):
        rows = []
        if groups:
            named_tuple = namedtuple('user', {**groups[0]}.keys())
            for group in groups:
                row = {
                    **group,
                    'users': json.loads(group['users'] or '[]'),
                    'tags': json.loads(group['tags'] or '[]'),
                    'attributes': json.loads(group['attributes'] or '{}')
                }
                rows.append(named_tuple(*row.values()))
        return rows

    def _distinct_users_query(self):
        return """
            SELECT IFNULL(json_arrayagg(user), '[]')
            FROM
            (SELECT DISTINCT t.user
             FROM JSON_TABLE(
                    JSON_MERGE(IFNULL(`groups`.`users`, '[]'), %(users)s),
                    "$[*]" columns (user varchar(255) PATH "$")
                )
             t) AS TEMP
        """

    def create_group(self, group):
        insert = """
            INSERT INTO `groups` (id, name, text)
            VALUES (%(id)s, %(name)s, %(text)s)
        """
        self._insert(insert, self._vars(group))

        select = """
            SELECT *, 0 AS count FROM `groups`
             WHERE id=%(id)s
        """
        return self._format_group(self._fetchone(select, self._vars(group)))

    def get_group(self, id):
        # CARDINALITY != json_length
        select = """SELECT *, COALESCE(JSON_LENGTH(users), 0) AS count FROM `groups` WHERE id=%(id)s"""
        return self._format_group(self._fetchone(select, {'id': id}))

    def get_groups(self, query=None, page=None, page_size=None):
        query = query or Query()
        select = """
            SELECT *, COALESCE(JSON_LENGTH(users), 0) AS count FROM `groups`
             WHERE {where}
          ORDER BY {order}
        """.format(where=query.where, order=query.sort)
        groups = self._fetchall(select, query.vars, limit=page_size, offset=(page - 1) * page_size)
        return self._format_groups(groups)

    def get_groups_count(self, query=None):
        query = query or Query()
        select = f"""
            SELECT COUNT(1) AS count FROM `groups`
             WHERE {query.where}
        """
        return self._fetchone(select, query.vars)['count']

    def get_group_users(self, id):
        select = """
            SELECT u.id, u.login, u.email, u.name, u.status
              FROM
                (SELECT id, t.user as uid
                 FROM `groups`,
                  JSON_TABLE(`groups`.users, "$[*]" columns (user varchar(255) PATH "$")) t
                ) g
            INNER JOIN users u on g.uid = u.id
            WHERE g.id = %(id)s
        """
        users = self._fetchall(select, {'id': id})
        return [dict(u) for u in users]

    def update_group(self, id, **kwargs):
        update = """
            UPDATE `groups`
            SET
        """
        if kwargs.get('name', None) is not None:
            update += 'name=%(name)s, '
        if kwargs.get('text', None) is not None:
            update += 'text=%(text)s, '
        update += """
            update_time=UTC_TIMESTAMP(3)
            WHERE id=%(id)s
        """
        kwargs['id'] = id
        self._updateone(update, kwargs)

        select = """
            SELECT *, COALESCE(JSON_LENGTH(users), 0) AS count
            FROM `groups`
            WHERE id=%(id)s
        """
        return self._format_group(self._fetchone(select, kwargs))

    def add_user_to_group(self, group, user):
        update = """
            UPDATE `groups`
            SET users=({distinct_users})
            WHERE id=%(id)s
        """.format(distinct_users=self._distinct_users_query())
        self._updateone(update, {'id': group, 'users': json.dumps([user])})

        select = """
            SELECT * FROM `groups`
            WHERE id=%(id)s
        """
        return self._format_group(self._fetchone(select, {'id': group}))

    def remove_user_from_group(self, group, user):
        update = """
            UPDATE groups
            SET users=(
                SELECT JSON_ARRAYAGG(t.user)
                FROM JSON_TABLE(`groups`.users, "$[*]" columns (user varchar(255) PATH "$")) t
                WHERE NOT t.user=%(user)s
            )
            WHERE id=%(id)s
        """
        self._updateone(update, {'id': group, 'user': user})

        select = """
            SELECT * FROM groups
            WHERE id=%(id)s
        """
        return self._format_group(self._fetchone(select, {'id': group}))

    def delete_group(self, id):
        delete = """
            DELETE FROM `groups`
            WHERE id=%(id)s
        """
        self._deleteone(delete, {'id': id})
        return id

    def get_groups_by_user(self, user):
        select = """
            SELECT *, COALESCE(JSON_LENGTH(users), 0) AS count
              FROM `groups`
            WHERE JSON_CONTAINS(users, JSON_QUOTE(%(user)s))
        """

        groups = self._fetchall(select, {'user': user})
        return self._format_groups(groups)

    # PERMISSIONS

    def _format_perm(self, perm):
        if perm:
            row = {
                **perm,
                'scopes': json.loads(perm['scopes'])
            }
            named_tuple = namedtuple('perm', row.keys())
            return named_tuple(*row.values())

    def _format_perms(self, perms):
        rows = []
        if perms:
            named_tuple = namedtuple('user', {**perms[0]}.keys())
            for perm in perms:
                row = {
                    **perm,
                    'scopes': json.loads(perm['scopes'])
                }
                rows.append(named_tuple(*row.values()))
        return rows

    def create_perm(self, perm):
        insert = """
            INSERT INTO perms (id, `match`, scopes)
            VALUES (%(id)s, %(match)s, %(scopes)s)
        """
        self._insert(insert, {**self._vars(perm), 'scopes': json.dumps(perm.scopes or [])})

        select = """
            SELECT * FROM perms
             WHERE id=%(id)s
        """
        return self._format_perm(self._fetchone(select, self._vars(perm)))

    def get_perm(self, id):
        select = """SELECT * FROM perms WHERE id=%(id)s"""
        return self._format_perm(self._fetchone(select, {'id': id}))

    def get_perms(self, query=None, page=None, page_size=None):
        query = query or Query()
        select = f"""
            SELECT * FROM perms
             WHERE {query.where}
          ORDER BY {query.sort}
        """
        perms = self._fetchall(select, query.vars, limit=page_size, offset=(page - 1) * page_size)
        return self._format_perms(perms)

    def get_perms_count(self, query=None):
        query = query or Query()
        select = f"""
            SELECT COUNT(1) AS count FROM perms
             WHERE {query.where}
        """
        return self._fetchone(select, query.vars)['count']

    def update_perm(self, id, **kwargs):
        update = """
            UPDATE perms
            SET
        """
        if 'match' in kwargs:
            update += '`match`=%(match)s, '
        if 'scopes' in kwargs:
            update += 'scopes=%(scopes)s, '
            kwargs['scopes'] = json.dumps(kwargs['scopes'] or [])
        update += """
            id=%(id)s
            WHERE id=%(id)s
        """
        kwargs['id'] = id
        self._updateone(update, kwargs)

        select = """SELECT * FROM perms WHERE id=%(id)s"""
        return self._format_perm(self._fetchone(select, {'id': id}))

    def delete_perm(self, id):
        delete = """
            DELETE FROM perms
            WHERE id=%(id)s
        """
        self._deleteone(delete, {'id': id})
        return id

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
            select = """SELECT scopes FROM perms WHERE `match`=%(match)s"""
            response = self._fetchone(select, {'match': match})
            if response:
                scopes.extend(json.loads(response['scopes']))
        return sorted(set(scopes))

    # CUSTOMERS

    def create_customer(self, customer):
        insert = """
            INSERT INTO customers (id, `match`, customer)
            VALUES (%(id)s, %(match)s, %(customer)s)
        """
        self._insert(insert, self._vars(customer))

        select = """
            SELECT * FROM customers
            WHERE id=%(id)s
        """
        return dict(self._fetchone(select, self._vars(customer)))

    def get_customer(self, id):
        select = """SELECT * FROM customers WHERE id=%(id)s"""
        return dict(self._fetchone(select, {'id': id}))

    def get_customers(self, query=None, page=None, page_size=None):
        query = query or Query()
        select = f"""
            SELECT * FROM customers
             WHERE {query.where}
          ORDER BY {query.sort}
        """
        return [dict(c) for c in self._fetchall(select, query.vars, limit=page_size, offset=(page - 1) * page_size)]

    def get_customers_count(self, query=None):
        query = query or Query()
        select = f"""
            SELECT COUNT(1) AS count FROM customers
             WHERE {query.where}
        """
        return self._fetchone(select, query.vars)['count']

    def update_customer(self, id, **kwargs):
        update = """
            UPDATE customers
            SET
        """
        if 'match' in kwargs:
            update += '`match`=%(match)s, '
        if 'customer' in kwargs:
            update += 'customer=%(customer)s, '
        update += """
            id=%(id)s
            WHERE id=%(id)s
        """
        kwargs['id'] = id
        self._updateone(update, kwargs)

        select = """SELECT * FROM customers WHERE id=%(id)s"""
        return dict(self._fetchone(select, {'id': id}))

    def delete_customer(self, id):
        delete = """
            DELETE FROM customers
            WHERE id=%(id)s
        """
        self._deleteone(delete, {'id': id})
        return id

    def get_customers_by_match(self, login, matches):
        if login in current_app.config['ADMIN_USERS']:
            return '*'  # all customers

        customers = []
        for match in [login] + matches:
            select = """SELECT customer FROM customers WHERE `match`=%(match)s"""
            response = self._fetchall(select, {'match': match})
            if response:
                customers.extend([r['customer'] for r in response])

        if customers:
            if '*' in customers:
                return '*'  # all customers
            return customers

        raise NoCustomerMatch(f"No customer lookup configured for user '{login}' or '{','.join(matches)}'")

    # NOTES
    def _format_note(self, note):
        if note:
            row = {
                **note,
                'attributes': json.loads(note['attributes']),
            }
            named_tuple = namedtuple('note', row.keys())
            return named_tuple(*row.values())

    def _format_notes(self, notes):
        rows = []
        if notes:
            named_tuple = namedtuple('note', {**notes[0]}.keys())
            for note in notes:
                row = {
                    **note,
                    'attributes': json.loads(note['attributes']),
                }
                rows.append(named_tuple(*row.values()))
        return rows

    def create_note(self, note):
        insert = """
            INSERT INTO notes (id, text, `user`, attributes, type,
                create_time, update_time, alert, customer)
            VALUES (%(id)s, %(text)s, %(user)s, %(attributes)s, %(note_type)s,
                %(create_time)s, %(update_time)s, %(alert)s, %(customer)s)
        """
        self._insert(insert, {**self._vars(note), 'attributes': json.dumps(note.attributes or {})})

        select = """SELECT * FROM notes WHERE id=%(id)s"""
        return self._format_note(self._fetchone(select, self._vars(note)))

    def get_note(self, id):
        select = """SELECT * FROM notes WHERE id=%(id)s"""
        return self._format_note(self._fetchone(select, {'id': id}))

    def get_notes(self, query=None, page=None, page_size=None):
        query = query or Query()
        select = f"""
            SELECT * FROM notes
             WHERE {query.where}
          ORDER BY {query.sort or 'create_time'}
        """
        notes = self._fetchall(select, query.vars, limit=page_size, offset=(page - 1) * page_size)
        return self._format_notes(notes)

    def get_alert_notes(self, id, page=None, page_size=None):
        select = """
            SELECT * FROM notes
             WHERE LOWER(alert) REGEXP LOWER(%(id)s)
        """
        notes = self._fetchall(select, {'id': id}, limit=page_size, offset=(page - 1) * page_size)
        return self._format_notes(notes)

    def get_customer_notes(self, customer, page=None, page_size=None):
        select = """
            SELECT * FROM notes
             WHERE customer=%(customer)s
        """
        notes = self._fetchall(select, (customer,), limit=page_size, offset=(page - 1) * page_size)
        return self._format_notes(notes)

    def update_note(self, id, **kwargs):
        update = """
            UPDATE notes
            SET
        """
        if kwargs.get('text', None) is not None:
            update += 'text=%(text)s, '
        if kwargs.get('attributes', None) is not None:
            update += 'JSON_MERGE_PATCH(IFNULL(attributes, "{}"), %(attributes)s), '
            kwargs['attributes'] = json.dumps(kwargs['attributes'] or {})
        update += """
            `user`=COALESCE(%(user)s, `user`),
            update_time=UTC_TIMESTAMP(3)
            WHERE id=%(id)s
        """
        kwargs['id'] = id
        kwargs['user'] = kwargs.get('user')
        self._updateone(update, kwargs)

        select = """SELECT * FROM notes WHERE id=%(id)s"""
        return self._format_note(self._fetchone(select, {'id': id}))

    def delete_note(self, id):
        delete = """
            DELETE FROM notes
            WHERE id=%(id)s
        """
        self._deleteone(delete, {'id': id})
        return id

    # METRICS

    def _format_metric(self, metric):
        if metric:
            row = {**metric}
            named_tuple = namedtuple('metric', row.keys())
            return named_tuple(*row.values())

    def get_metrics(self, type=None):
        select = """SELECT * FROM metrics"""
        if type:
            select += ' WHERE type=%(type)s'
        metrics = self._fetchall(select, {'type': type})
        return [self._format_metric(m) for m in metrics]

    def set_gauge(self, gauge):
        upsert = """
            INSERT INTO metrics (`group`, name, title, description, value, type)
            VALUES (%(group)s, %(name)s, %(title)s, %(description)s, %(value)s, %(type)s)
            ON DUPLICATE KEY
             UPDATE value=%(value)s
        """
        self._upsert(upsert, self._vars(gauge))

        select = """
            select * from metrics
            where `group`=%(group)s AND name=%(name)s AND type=%(type)s
        """
        return self._format_metric(self._fetchone(select, self._vars(gauge)))

    def inc_counter(self, counter):
        upsert = """
            INSERT INTO metrics (`group`, name, title, description, count, type)
            VALUES (%(group)s, %(name)s, %(title)s, %(description)s, %(count)s, %(type)s)
            ON DUPLICATE KEY
                UPDATE count=metrics.count + %(count)s
        """
        self._upsert(upsert, self._vars(counter))

        select = """
            select * from metrics
            where `group`=%(group)s AND name=%(name)s AND type=%(type)s
        """
        return self._format_metric(self._fetchone(select, self._vars(counter)))

    def update_timer(self, timer):
        upsert = """
            INSERT INTO metrics (`group`, name, title, description, count, total_time, type)
            VALUES (%(group)s, %(name)s, %(title)s, %(description)s, %(count)s, %(total_time)s, %(type)s)
            ON DUPLICATE KEY UPDATE
                count=metrics.count + %(count)s, total_time=metrics.total_time + %(total_time)s
        """
        self._upsert(upsert, self._vars(timer))

        select = """
            SELECT * FROM metrics
            where `group`=%(group)s AND name=%(name)s AND type=%(type)s
        """
        return self._format_metric(self._fetchone(select, self._vars(timer)))

    # HOUSEKEEPING

    def get_expired(self, expired_threshold, info_threshold):
        # delete 'closed' or 'expired' alerts older than "expired_threshold" seconds
        # and 'informational' alerts older than "info_threshold" seconds

        if expired_threshold:
            delete = """
                DELETE FROM alerts
                 WHERE (status IN ('closed', 'expired')
                        AND last_receive_time < (UTC_TIMESTAMP(3) - INTERVAL %(expired_threshold)s second))
            """
            self._deleteall(delete, {'expired_threshold': expired_threshold})

        if info_threshold:
            delete = """
                DELETE FROM alerts
                 WHERE (severity=%(inform_severity)s
                        AND last_receive_time < (UTC_TIMESTAMP(3) - INTERVAL %(info_threshold)s second))
            """
            self._deleteall(delete, {'inform_severity': alarm_model.DEFAULT_INFORM_SEVERITY, 'info_threshold': info_threshold})

        # get list of alerts to be newly expired
        select = """
            SELECT *
              FROM alerts
             WHERE status NOT IN ('expired') AND COALESCE(timeout, {timeout})!=0
               AND (last_receive_time + INTERVAL 1 * timeout second) < UTC_TIMESTAMP(3)
        """.format(timeout=current_app.config['ALERT_TIMEOUT'])

        alerts = self._fetchall(select, {})
        return [self._format_alert(alert) for alert in alerts]

    def get_unshelve(self):
        # get list of alerts to be unshelved
        select = """
            SELECT DISTINCT a.*
              FROM alerts a,
                   JSON_TABLE(a.history,
                   "$[*]" columns(
                       type    varchar(500) path "$.type",
                       status  varchar(500) path "$.status",
                       timeout int          path "$.timeout"
                   )) h
             WHERE a.status='shelved'
               AND h.type='shelve'
               AND h.status='shelved'
               AND COALESCE(h.timeout, {timeout})!=0
               AND (a.update_time + INTERVAL 1 * h.timeout second) < UTC_TIMESTAMP(3)
          GROUP BY a.id
          ORDER BY a.id, a.update_time DESC
        """.format(timeout=current_app.config['SHELVE_TIMEOUT'])
        alerts = self._fetchall(select, {})
        return [self._format_alert(alert) for alert in alerts]

    def get_unack(self):
        # get list of alerts to be unack'ed
        select = """
            SELECT DISTINCT a.*
              FROM alerts a,
                   JSON_TABLE(a.history,
                    "$[*]" columns(
                        type    varchar(500) path "$.type",
                        status  varchar(500) path "$.status",
                        timeout int          path "$.timeout"
                    )) h
             WHERE a.status='ack'
               AND h.type='ack'
               AND h.status='ack'
               AND COALESCE(h.timeout, {timeout})!=0
               AND (a.update_time + INTERVAL 1 * h.timeout second) < UTC_TIMESTAMP(3)
          GROUP BY a.id
          ORDER BY a.id, a.update_time DESC
        """.format(timeout=current_app.config['ACK_TIMEOUT'])
        alerts = self._fetchall(select, {})
        return [self._format_alert(alert) for alert in alerts]

    # SQL HELPERS

    def _vars(self, args):
        kwargs = {}
        args = vars(args)
        for key, value in args.items():
            if isinstance(value, (dict, list, tuple)):
                kwargs[key] = custom_json_dumps(value)
            else:
                kwargs[key] = value
        return kwargs

    def _insert(self, query, vars):
        """
        Insert, with return.
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self._log(cursor, query, vars)
        cursor.execute(query, vars)
        conn.commit()

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
        query += f' LIMIT {limit} OFFSET {offset}'
        cursor = self.get_db().cursor()
        self._log(cursor, query, vars)
        cursor.execute(query, vars)
        return cursor.fetchall()

    def _updateone(self, query, vars, returning=False):
        """
        Update, with optional return.
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self._log(cursor, query, vars)
        cursor.execute(query, vars)
        conn.commit()

    def _updateall(self, query, vars, returning=False):
        """
        Update, with optional return.
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self._log(cursor, query, vars)
        cursor.execute(query, vars)
        conn.commit()

    def _upsert(self, query, vars):
        """
        Insert or update, with return.
        """
        self._insert(query, vars)

    def _deleteone(self, query, vars, returning=False):
        """
        Delete, with optional return.
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self._log(cursor, query, vars)
        cursor.execute(query, vars)
        conn.commit()

    def _deleteall(self, query, vars, returning=False):
        """
        Delete multiple rows, with optional return.
        """
        conn = self.get_db()
        cursor = conn.cursor()
        self._log(cursor, query, vars)
        cursor.execute(query, vars)
        conn.commit()

    def _log(self, cursor, query, vars):
        current_app.logger.debug('{stars}\n{query}\n{stars}'.format(
            stars='*' * 40, query=cursor.mogrify(query, vars)))
