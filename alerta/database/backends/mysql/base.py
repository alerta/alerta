import time
from collections import namedtuple
from datetime import datetime, date

import mysql.connector
from mysql.connector import errorcode

import json
import re
import pprint

from flask import current_app, g

from alerta.database.base import Database
from alerta.exceptions import NoCustomerMatch
from alerta.utils.api import absolute_url
from alerta.utils.format import DateTime
from alerta.models.history import History, RichHistory
from .utils import Query

MAX_RETRIES = 5

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))

class HistoryEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        if isinstance(o, list):
            return json.dumps(list).replace("'",'"')
        return o.serialize

class MySQLCursorDict(mysql.connector.cursor.MySQLCursor):
    def _row_to_python(self, rowdata, desc=None):
        row = super(MySQLCursorDict, self)._row_to_python(rowdata, desc)
        if row:
            return dict(zip(self.column_names, row))
        return None

class HistoryAdapter(object):
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

        return "(%s, %s, %s, %s, %s, %s, %s, %s::timestamp)::history" % (
            quoted(self.history.id),
            quoted(self.history.event),
            quoted(self.history.severity),
            quoted(self.history.status),
            quoted(self.history.value),
            quoted(self.history.text),
            quoted(self.history.change_type),
            quoted(self.history.update_time)
        )

    def __str__(self):
        return str(self.getquoted())

class Backend(Database):

    def execute_first_command(self, conn, commands, delimiter):
        position = commands.find(delimiter)
        if position < 0:
            return ''
        command = commands[:position]
        print(command)
        cursor = conn.cursor()
        cursor.execute(command)
        conn.commit()
        cursor.close()
        return commands[position+len(delimiter):].lstrip()

    def create_engine(self, app, uri, dbname=None): 
        mysql_regex = re.compile("([^:]+)://([^:]+):([^@]+)@([^:]+):([^/]+)/([^/]+)")
        pattern = mysql_regex.match(uri)
        self.uri = uri
        self.port = pattern.group(5)
        self.host = pattern.group(4)
        self.username = pattern.group(2)
        self.password = pattern.group(3)
        self.dbname = pattern.group(6)
    
        print(uri)
        conn = self.connect()
        print('connected ok')
        with app.open_resource('sql/mysql-schema.sql') as f:
            #conn.cursor().execute(f.read())
            file_content = f.read()
            #conn.commit()


        print('creating schema')

        hay_comandos = True
        comandos_restantes = file_content.lstrip()
        delimiter = ';'
        delimiter_match = re.compile("[\s]*[Dd][Ee][Ll][Ii][Mm][Ii][Tt][Ee][Rr][\s]+([\S]*)")
        while hay_comandos:
            pattern = delimiter_match.match(comandos_restantes.lstrip())
            if pattern:
                delimiter = pattern.group(1)
                position = comandos_restantes.find(delimiter)
                comandos_restantes = comandos_restantes[position+len(delimiter)+1:].lstrip()

            comandos_restantes = self.execute_first_command(conn, comandos_restantes, delimiter)
            if len(comandos_restantes) == 0:
                hay_comandos = False

        '''
        delimiter_command = False
        for command in file_content.split(';'):
            if len(command) > 0:
                if 'DELIMITER ;' in command:
                    delimiter_command = False
                elif delimiter_command == False and 'DELIMITER' in command:
                    delimiter = re.match('DELIMITER ([^\n]*)', command).group(1)
                    delimiter_command = True
                    accumulated_command = ""
                    cursor = conn.cursor()
                    cursor.execute(command)
                    conn.commit()
                    cursor.close()
                elif delimiter_command == True:
                    if delimiter in command:
                        accumulated_command += command
                        cursor = conn.cursor()
                        cursor.execute(command + ';')
                        conn.commit()
                        cursor.close()
                    else:
                        accumulated_command += command + ';'
                else:
                    cursor = conn.cursor()
                    cursor.execute(command + ';')
                    conn.commit()
                    cursor.close()
        '''

#        register_adapter(dict, Json)
#        register_adapter(datetime, self._adapt_datetime)
#        register_composite(
#            'history',
#            conn,
#            globally=True
#        )
        from alerta.models.alert import History
#        register_adapter(History, HistoryAdapter)


    def connect(self):
        retry = 0
        while True:
            try:
                conn = mysql.connector.connect(
                    host=self.host,
                    port=self.port,
                    user=self.username,
                    password=self.password,
                    database=self.dbname
                )
                break
            except mysql.connector.Error as err:
                if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                    print("Something is wrong with credentials")
                elif err.errno == errorcode.ER_BAD_DB_ERROR:
                    print("Database does not exist")
                else:
                    print(err)
            else:
                conn.close()

        if conn:
            return conn
        else:
            raise RuntimeError('Database connect error. Failed to connect after {} retries.'.format(MAX_RETRIES))

    @staticmethod
    def _adapt_datetime(dt):
        return AsIs("%s" % adapt(DateTime.iso8601(dt)))

    @property
    def name(self):
        cursor = g.db.cursor()
        cursor.execute("SELECT database()")
        return cursor.fetchone()[0]

    @property
    def version(self):
        cursor = g.db.cursor()
        cursor.execute("SHOW VARIABLES LIKE '%version%'")
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
        for table in ['alerts', 'blackouts', 'customers', 'heartbeats', '`keys`', '`metrics`', '`perms`', '`users`']:
            cursor.execute("DROP TABLE IF EXISTS %s" % table)
        cursor.execute('DROP PROCEDURE IF EXISTS test_index')
        conn.commit()
        conn.close()

    #### ALERTS

    def pre_process_alert(self,alert_object):
        alert_object['id'] = alert_object['id'].encode('ascii','ignore')
        alert_object['group'] = alert_object['group'].encode('ascii','ignore')
        alert_object['origin'] = alert_object['origin'].encode('ascii','ignore')
        alert_object['previousSeverity'] = alert_object['previous_severity'].encode('ascii','ignore')
        alert_object['trendIndication'] = alert_object['trend_indication'].encode('ascii','ignore')
        alert_object['receiveTime'] = alert_object['receive_time']
        alert_object['lastReceiveId'] = alert_object['last_receive_id']
        alert_object['lastReceiveTime'] = alert_object['last_receive_time']

        alert_object['rawData'] = alert_object['raw_data'].encode('ascii','ignore') if alert_object['raw_data'] else alert_object['raw_data']
        alert_object['status'] = alert_object['status'].encode('ascii','ignore')
        alert_object['duplicateCount'] = alert_object['duplicate_count']

        #alert_object['event_type'] = alert_object['event_type'].encode('ascii','ignore')
        alert_object['attributes'] = json.loads(alert_object['attributes'])
        alert_object['history'] = json.loads(alert_object['history'])
        alert_object['tags'] = json.loads(alert_object['tags'])
        alert_object['correlate'] = json.loads(alert_object['correlate'])
        alert_object['service'] = json.loads(alert_object['service'])
        alert_object['repeat'] = True if alert_object['repeat'] == 1 else False
        if 'tags' in alert_object:
            print(alert_object['tags'])
            for i in range(len(alert_object['tags'])):
                alert_object['tags'][i] = alert_object['tags'][i].encode('ascii','ignore')
            #alert_object['tags'] = json.loads(alert_object['tags'])

        #alert_object['history'] = [History.from_document(x) for x in alert_object['history'] if x]
        for i in range(len(alert_object['history'])):
            if type(alert_object['history'][i]) == unicode:
                alert_object['history'][i] = json.loads(alert_object['history'][i])
        #alert_object['history'] = [x for x in alert_object['history'] if x]
        for x in alert_object['history']:
            print ("History (%s): %s" % (type(x),x))

    def serialize_for_json_append(self,history_list, string=",'$','%s'"):
        if history_list is None:
            return None
        hstr = ""
        if type(history_list) == list:
            for h in history_list:
                hjson = json.dumps(h, cls=HistoryEncoder)
                hstr += string % hjson
        else:
            hjson = json.dumps(history_list, cls=HistoryEncoder)
            hstr += ",'$','%s'" % hjson
        return hstr

    def get_severity(self, alert):
        select = """
            SELECT severity FROM alerts
             WHERE environment='%(environment)s' AND resource='%(resource)s'
               AND ((event='%(event)s' AND severity!='%(severity)s')
                OR (event!='%(event)s' AND JSON_SEARCH(correlate,'one','%(event)s') > 0))
               AND {customer}
            """.format(customer="customer='%(customer)s'" if alert.customer else "customer IS NULL")
        return self._fetchone(select, vars(alert)).severity

    def get_status(self, alert):
        select = """
            SELECT status FROM alerts
             WHERE environment='%(environment)s' AND resource='%(resource)s'
              AND (event='%(event)s' OR JSON_SEARCH(correlate,'one','%(event)s') > 0)
              AND {customer}
            """.format(customer="customer=%(customer)s" if alert.customer else "customer IS NULL")
        return self._fetchone(select, vars(alert)).status

    def get_status_and_value(self, alert):

        print("Alert customer: %s" % type(alert.customer))
        select = """
            SELECT status, value FROM alerts
             WHERE environment='%(environment)s' AND resource='%(resource)s'
              AND (event='%(event)s' OR JSON_SEARCH(correlate,'one','%(event)s') > 0)
              AND {customer}
            """.format(customer="customer=%(customer)s" if alert.customer else "customer IS NULL")
        r = self._fetchone(select, vars(alert))
        return r.status, r.value

    def is_duplicate(self, alert):
        select = """
            SELECT id FROM alerts
             WHERE environment='%(environment)s'
               AND resource='%(resource)s'
               AND event='%(event)s'
               AND severity='%(severity)s'
               AND {customer}
            """.format(customer="customer='%(customer)s'" if alert.customer else "customer IS NULL")
        return bool(self._fetchone(select, vars(alert)))

    def is_correlated(self, alert):
        select = """
            SELECT id FROM alerts
             WHERE environment='%(environment)s' AND resource='%(resource)s'
               AND ((event='%(event)s' AND severity!='%(severity)s')
                OR (event!='%(event)s' AND JSON_SEARCH(correlate,'one','%(event)s') > 0))
               AND {customer}
        """.format(customer="customer='%(customer)s'" if alert.customer else "customer IS NULL")
        return bool(self._fetchone(select, vars(alert)))

    def is_flapping(self, alert, window=1800, count=2):
        """
        Return true if alert severity has changed more than X times in Y seconds
        """
        select = """
            SELECT COUNT(*)
              FROM alerts, unnest(history) h
             WHERE environment='%(environment)s'
               AND resource='%(resource)s'
               AND h.event='%(event)s'
               AND h.update_time > (NOW() at time zone 'utc' - INTERVAL '{window} seconds')
               AND h.type='severity'
               AND {customer}
        """.format(window=window, customer="customer='%(customer)s'" if alert.customer else "customer IS NULL")
        return self._fetchone(select, vars(alert)).count > count

    def dedup_alert(self, alert, history):
        """
        Update alert value, text and rawData, increment duplicate count and set repeat=True, and
        keep track of last receive id and time but don't append to history unless status changes.
        """
        alert.history = history
        print("History Type: %s" % type(alert.history))
        history_update = self.serialize_for_json_append(alert.history)
        history_update_string = ", history=JSON_ARRAY_APPEND(history {histories})".format(histories=history_update)

        tag_update = self.serialize_for_json_append(alert.tags,",'$',%s")
        tags_update_string = """, tags=JSON_ARRAY_APPEND(tags {tags})""".format(tags=tag_update)

        update = """
            UPDATE alerts
               SET status='%(status)s', value={value}, text='%(text)s', timeout=%(timeout)s, raw_data={raw_data}, `repeat`=%(repeat)s,
                   last_receive_id='%(last_receive_id)s', last_receive_time='%(last_receive_time)s' {tags}, attributes=JSON_MERGE(attributes ,'%(attributes)s'),
                   duplicate_count=duplicate_count+1 {history}
             WHERE environment='%(environment)s'
               AND resource='%(resource)s'
               AND event='%(event)s'
               AND severity='%(severity)s'
               AND {customer}
        """.format(limit=current_app.config['HISTORY_LIMIT'], customer="customer='%(customer)s'" if alert.customer else "customer IS NULL",
                    value="'%(value)s'" if alert.value else "NULL",raw_data="'%(raw_data)s'" if alert.raw_data else "NULL",
                    history=history_update_string if alert.history and (isinstance(alert.history,History) or len(alert.history)) > 0 else "",
                    tags=tags_update_string if alert.tags and len(alert.tags) > 0 else "")

        #print("History Type: %s" % type(alert.history))
        data = vars(alert)
        data['repeat'] = 1 if json.dumps(data['repeat'], cls=HistoryEncoder) == 'false' else 0 
        data['attributes'] = json.dumps(data['attributes'], cls=HistoryEncoder)
        data['history'] = json.dumps(data['history'], cls=HistoryEncoder)

        get_query = '''SELECT * FROM alerts WHERE environment='%(environment)s'
               AND resource='%(resource)s'
               AND event='%(event)s'
               AND severity='%(severity)s'
               AND {customer}'''.format(limit=current_app.config['HISTORY_LIMIT'], customer="customer='%(customer)s'" if alert.customer else "customer IS NULL",
                    value="'%(value)s'" if alert.value else "NULL",raw_data="'%(raw_data)s'" if alert.raw_data else "NULL",
                    history=", history=JSON_ARRAY_APPEND(history,'$','%(history)s')" if alert.history else "")

        self._update(update, data)
        alert_object = self._fetchone(get_query,data)

        alert_object = alert_object._asdict()
        
        self.pre_process_alert(alert_object)

        return alert_object

    def correlate_alert(self, alert, history):

        alert.history = history

        #print("History Type: %s" % type(alert.history))
        history_update = self.serialize_for_json_append(alert.history)
        history_update_string = ", history=JSON_ARRAY_APPEND(history {histories})".format(histories=history_update)

        tag_update = self.serialize_for_json_append(alert.tags, ",'$',%s")
        tags_update_string = """, tags=JSON_ARRAY_APPEND(tags {tags})""".format(tags=tag_update)

        update = """
            UPDATE alerts
               SET event='%(event)s', severity='%(severity)s', status='%(status)s', value={value}, text='%(text)s',
                   create_time='%(create_time)s', timeout='%(timeout)s', raw_data={raw_data}, duplicate_count=%(duplicate_count)s,
                   `repeat`=%(repeat)s, previous_severity='%(previous_severity)s', trend_indication='%(trend_indication)s',
                   receive_time='%(receive_time)s', last_receive_id='%(last_receive_id)s',
                   last_receive_time='%(last_receive_time)s' {tags},
                   attributes=JSON_MERGE(attributes ,'%(attributes)s') {history}
             WHERE environment='%(environment)s' AND resource='%(resource)s'
               AND ((event='%(event)s' AND severity!='%(severity)s') OR (event!='%(event)s' AND JSON_SEARCH(correlate,'one','%(event)s') > 0) )
               AND {customer}
        """.format(limit=current_app.config['HISTORY_LIMIT'], 
                customer="customer='%(customer)s'" if alert.customer else "customer IS NULL",
                value="'%(value)s'" if alert.value else "NULL",
                raw_data="'%(raw_data)s'" if alert.raw_data else "NULL",
                history=history_update_string if alert.history and (isinstance(alert.history,History) or len(alert.history)) > 0 else "",
                tags=tags_update_string if alert.tags and len(alert.tags) > 0 else "")
        
        data = vars(alert)
        data['repeat'] = 1 if json.dumps(data['repeat'], cls=HistoryEncoder) == 'false' else 0 
        data['attributes'] = json.dumps(data['attributes'], cls=HistoryEncoder)
        #data['history'] = json.dumps(data['history'], cls=HistoryEncoder)
        data['tags'] = json.dumps(data['tags'], cls=HistoryEncoder)

        get_query = '''SELECT * FROM alerts WHERE environment='%(environment)s'
               AND resource='%(resource)s'
               AND event='%(event)s' AND severity='%(severity)s' AND {customer}
        '''.format(limit=current_app.config['HISTORY_LIMIT'], 
                customer="customer='%(customer)s'" if alert.customer else "customer IS NULL",
                value="'%(value)s'" if alert.value else "NULL",
                raw_data="'%(raw_data)s'" if alert.raw_data else "NULL")

        self._update(update, data)
        alert_object = self._fetchone(get_query,data)
        alert_object = alert_object._asdict()      
        self.pre_process_alert(alert_object)
        return alert_object

    def create_alert(self, alert):
        insert = """
            INSERT INTO alerts (id, resource, event, environment, severity, correlate, status, service, `group`,
                value, `text`, `tags`, attributes, origin, type, create_time, timeout, raw_data, customer,
                duplicate_count, `repeat`, previous_severity, trend_indication, receive_time, last_receive_id,
                last_receive_time, history)
            VALUES ('%(id)s', '%(resource)s', '%(event)s', '%(environment)s', '%(severity)s', '%(correlate)s', '%(status)s',
                '%(service)s', '%(group)s', {value}, '%(text)s', '%(tags)s', '%(attributes)s', '%(origin)s',
                '%(event_type)s', '%(create_time)s', '%(timeout)s', {raw_data}, {customer}, '%(duplicate_count)s',
                '%(repeat)s', '%(previous_severity)s', '%(trend_indication)s', '%(receive_time)s', '%(last_receive_id)s',
                '%(last_receive_time)s', '%(history)s')
        """.format(customer="customer='%(customer)s'" if alert.customer else "NULL",
            value="'%(value)s'" if alert.value else "NULL",
            raw_data="'%(raw_data)s'" if alert.raw_data else "NULL")

        print("Tags Type: %s" % alert.tags)
        data = vars(alert)
        #data['origin'] = json.dumps(data['origin'], cls=HistoryEncoder)
        data['repeat'] = 1 if json.dumps(data['repeat'], cls=HistoryEncoder) == 'false' else 0 
        data['attributes'] = json.dumps(data['attributes'], cls=HistoryEncoder)
        data['service'] = json.dumps(data['service'], cls=HistoryEncoder)
        data['correlate'] = json.dumps(data['correlate'], cls=HistoryEncoder)
        data['history'] = json.dumps(data['history'], cls=HistoryEncoder)
        data['tags'] = json.dumps(data['tags'], cls=HistoryEncoder)

        print("Alert DATA: %s" % pprint.pformat(data))
        get_query = "select * from alerts where id = '%(id)s'" 
        self._insert(insert, data)
        alert_object = self._fetchone(get_query,data)
        print("Object: %s" % pprint.pformat(alert_object))
        alert_object = alert_object._asdict()
        print("Attributes: %s" % alert_object['attributes'])
        #raise Exception('a')

        self.pre_process_alert(alert_object)

        print('PreParse Object: %s' % pprint.pformat(alert_object))

        #print("Object: %s" % pprint.pformat(alert))
        return alert_object

    def get_alert(self, id, customers=None):
        select = """
            SELECT * FROM alerts
             WHERE (id REGEXP ('%(id)s') OR last_receive_id REGEXP ('%(id)s'))
               AND {customer}
        """.format(customer="customer IN ('%(customers)s')" if customers else "1=1")
        #return self._fetchone(select, {'id': id, 'customers': customers})
        select = select % {"id":id,"customers":customers}
        alert_object = self._fetchone(select)
        if alert_object:
            alert_object = alert_object._asdict()      
            self.pre_process_alert(alert_object)
        return alert_object

    #### STATUS, TAGS, ATTRIBUTES

    def set_status(self, id, status, timeout, history=None):

        history_update = self.serialize_for_json_append(history)
        history_update_string = ", history=JSON_ARRAY_APPEND(history {histories})".format(histories=history_update)

        update = """
            UPDATE alerts
            SET status='%(status)s' {timeout} {history}
            WHERE id REGEXP '%(id)s'
        """.format(limit=current_app.config['HISTORY_LIMIT'],
            history=history_update_string if history and (isinstance(history,History) or len(history)) else "",
            timeout=', timeout=%(timeout)s' if timeout else "")
        data = {'id': id, 'like_id': id + '%', 'status': status, 'timeout': timeout}
        #return self._update(update, data, returning=True)
        get_query = "select * from alerts where id = '%(id)s'" 
        self._update(update, data, returning=True)
        alert_object = self._fetchone(get_query,data)
        alert_object = alert_object._asdict()      
        self.pre_process_alert(alert_object)
        return alert_object

    def set_severity_and_status(self, id, severity, status, timeout, history=None):

        history_update = self.serialize_for_json_append(history)
        history_update_string = ", history=JSON_ARRAY_APPEND(history {histories})".format(histories=history_update)

        update = """
            UPDATE alerts
            SET severity='%(severity)s', status='%(status)s' {timeout} {history}
            WHERE id REGEXP '%(id)s' 
        """.format(limit=current_app.config['HISTORY_LIMIT'],
            history=history_update_string if history and (isinstance(history,History) or len(history)) else "",
            timeout=', timeout=%(timeout)s' if timeout else "")

        data = {'id': id, 'like_id': id + '%', 'status': status, 'timeout': timeout, 'severity':severity}
        #return self._update(update, data, returning=True)
        get_query = "select * from alerts where id = '%(id)s'" 
        self._update(update, data, returning=True)
        alert_object = self._fetchone(get_query,data)
        alert_object = alert_object._asdict()      
        self.pre_process_alert(alert_object)
        return alert_object

    def tag_alert(self, id, tags):

        tag_update = self.serialize_for_json_append(tags,",'$',%s")
        tags_update_string = """tags=JSON_ARRAY_APPEND(tags {tags})""".format(tags=tag_update)
        tags_not_search = ''
        for tag in tags:
            #tags_not_search += " AND NOT JSON_SEARCH(tags,'one','%s') > 0 " % tag
            tags_not_search += " AND json_string_check('%(id)s','%(tag)s') < 1" % {"id":id,"tag":tag}

        update = """
            UPDATE alerts
            SET {tags}
            WHERE id REGEXP '%(id)s' {tags_not_search}
        """.format(tags=tags_update_string,tags_not_search=tags_not_search)
        data = {'id': id, 'like_id': id + '%', 'tags': tags}
        self._update(update, data, returning=True)
        select = """SELECT * FROM alerts WHERE id REGEXP '%(id)s'"""
        alert_object = self._fetchone(select,data)
        alert_object = alert_object._asdict() 
        self.pre_process_alert(alert_object)
        return alert_object

    def untag_alert(self, id, tags):

        print("Tags: %s" %tags)
        update = """
        UPDATE alerts 
        SET tags = JSON_REMOVE(tags,replace(json_search(tags,'one','%(tags)s'),'"','')) 
        WHERE json_search(tags,'one','bar') IS NOT NULL AND id REGEXP '%(id)s'
        """
        #self._update(update, {'id': id, 'like_id': id+'%', 'tags': tags[0]}, returning=True)
        data = {'id': id, 'like_id': id + '%', 'tags': tags[0]}
        self._update(update, data, returning=True)
        select = """SELECT * FROM alerts WHERE id REGEXP '%(id)s'"""
        alert_object = self._fetchone(select,data)
        alert_object = alert_object._asdict() 
        self.pre_process_alert(alert_object)
        return alert_object

    def update_attributes(self, id, old_attrs, new_attrs):
        old_attrs.update(new_attrs)
        attrs = dict([k, v] for k, v in old_attrs.items() if v is not None)
        update = """
            UPDATE alerts
            SET attributes='%(attrs)s'
            WHERE id REGEXP '%(id)s' 
        """
        data = {'id': id, 'like_id': id+'%', 'attrs': attrs}
        data['attrs'] = json.dumps(data['attrs'], cls=HistoryEncoder)
        self._update(update, data, returning=True)
        select = """SELECT * FROM alerts WHERE id REGEXP '%(id)s'"""
        alert_object = self._fetchone(select,data)
        alert_object = alert_object._asdict() 
        self.pre_process_alert(alert_object)
        return alert_object

    def delete_alert(self, id):
        delete = """
            DELETE FROM alerts
            WHERE id REGEXP '%(id)s' 
        """
        data = {'id': id, 'like_id': id+'%'}
        select = """SELECT id FROM alerts WHERE id REGEXP '%(id)s'"""
        alert_object = self._fetchone(select,data)
        alert_object = alert_object._asdict()  
        alert = {}
        alert['id'] = alert_object['id']


        self._delete(delete, data)
        return alert

    #### SEARCH & HISTORY

    def get_alerts(self, query=None, page=None, page_size=None):
        query = query or Query()
        select = """
            SELECT * FROM alerts
            WHERE {where}
            ORDER BY {order}
        """.format(where=query.where, order=query.sort or 'last_receive_time')
        #raise Exception(str(select % query.vars))
        alerts = self._fetchall(select, query.vars, limit=page_size, offset=(page - 1) * page_size)
        #print("FetchAll Len: %d" % len(alerts))
        for i in range(len(alerts)):
            alerts[i] = alerts[i]._asdict()
            self.pre_process_alert(alerts[i])
        #for x in alerts:
        #   print("Pre alert: %s" % pprint.pformat(x))
        #for alert in alerts:
        #    alert = alert._asdict()
        #    self.pre_process_alert(alert)
        #print('GetAlerts Object: %s' % pprint.pformat(alerts[0]))
        return alerts

    def get_history(self, query=None, page=None, page_size=None):
        query = query or Query()
        select = """
            SELECT resource, environment, service, `group`, tags, attributes, origin, customer,
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
            SELECT severity, COUNT(severity) as count FROM alerts
             WHERE {where}
            GROUP BY severity
        """.format(where=query.where)
        return dict([(s.severity, s.count) for s in self._fetchall(select, query.vars)])

    def get_counts_by_status(self, query=None):
        query = query or Query()
        select = """
            SELECT status, COUNT(status) as count FROM alerts
            WHERE {where}
            GROUP BY status
        """.format(where=query.where)
        return dict([(s.status, s.count) for s in self._fetchall(select, query.vars)])

    def get_topn_count(self, query=None, group="event", topn=10):
        query = query or Query()
        select = """
            SELECT event, COUNT(1) as count, SUM(duplicate_count) AS duplicate_count,
                   environment AS environments, service, resource
              FROM alerts
             WHERE {where}
          GROUP BY {group}
          ORDER BY count DESC
        """.format(where=query.where, group=group)
        return [
            {
                "count": t.count,
                "duplicateCount": t.duplicate_count,
                "environments": t.environments,
                "services": t.service,
                "%s" % group: t.event,
                "resources": [{"id": r[0], "resource": r[1], "href": absolute_url('/alert/%s' % r[0])} for r in t.resource]
            } for t in self._fetchall(select, query.vars, limit=topn)
        ]

    def get_topn_flapping(self, query=None, group="event", topn=10):
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
                "count": t.count,
                "duplicateCount": t.duplicate_count,
                "environments": t.environments,
                "services": t.services,
                "event": t.event,
                "resources": [{"id": r[0], "resource": r[1], "href": absolute_url('/alert/%s' % r[0])} for r in t.resources]
            } for t in self._fetchall(select, query.vars, limit=topn)
        ]

    def get_topn_standing(self, query=None, group="event", topn=10):
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
                "count": t.count,
                "duplicateCount": t.duplicate_count,
                "environments": t.environments,
                "services": t.services,
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
            INSERT INTO blackouts (id, priority, environment, service, resource, event, `group`, tags, customer, start_time, end_time, duration)
            VALUES (%(id)s, %(priority)s, %(environment)s, %(service)s, %(resource)s, %(event)s, %(group)s, %(tags)s, %(customer)s, %(start_time)s, %(end_time)s, %(duration)s)
            RETURNING *
        """
        return self._insert(insert, vars(blackout))

    def get_blackout(self, id, customer=None):
        select = """
            SELECT * FROM blackouts
            WHERE id=%(id)s
              AND {customer}
        """.format(customer="customer=%(customer)s" if customer else "1=1")
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
            WHERE start_time <= '%(now)s' AND end_time > '%(now)s'
              AND environment='%(environment)s'
              AND (
                 (resource IS NULL AND service='{}' AND event IS NULL AND `group` IS NULL AND tags='{}')
              OR (resource='%(resource)s' AND service='{}' AND event IS NULL AND `group` IS NULL AND tags='{}') 
              OR (resource IS NULL AND JSON_CONTAINS(service, '%(service)s') AND event IS NULL AND `group` IS NULL AND tags='{}')
              OR (resource IS NULL AND service='{}' AND event='%(event)s' AND `group` IS NULL AND tags='{}')
              OR (resource IS NULL AND service='{}' AND event IS NULL AND `group`='%(group)s' AND tags='{}')
              OR (resource='%(resource)s' AND service='{}' AND event='%(event)s' AND `group` IS NULL AND tags='{}')
              OR (resource IS NULL AND service='{}' AND event IS NULL AND `group` IS NULL AND JSON_CONTAINS(tags,'%(tags)s'))
                )
        """
        data = vars(alert)

        print("QueryData: %s" % pprint.pformat(data))
        data['service'] = json.dumps(data['service'])
        data['last_receive_time'] = json.dumps(data['last_receive_time'], cls=HistoryEncoder)
        data['history'] = json.dumps(data['history'], cls=HistoryEncoder)
        data['correlate'] = json.dumps(data['correlate'], cls=HistoryEncoder)
        data['tags'] = json.dumps(data['tags'], cls=HistoryEncoder)
        data['now'] = now
        if current_app.config['CUSTOMER_VIEWS']:
            select += " AND (customer IS NULL OR customer=%(customer)s)"

        select = select % data
        if self._fetchone(select):
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

    def get_heartbeat(self, id, customers=None):
        select = """
            SELECT * FROM heartbeats
             WHERE (id=%(id)s OR id LIKE %(like_id)s)
               AND {customer}
        """.format(customer="customer=%(customers)s" if customers else "1=1")
        return self._fetchone(select, {'id': id, 'like_id': id+'%', 'customers': customers})

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
            INSERT INTO `keys` (id, key, "user", scopes, text, expire_time, "count", last_used_time, customer)
            VALUES (%(id)s, %(key)s, %(user)s, %(scopes)s, %(text)s, %(expire_time)s, %(count)s, %(last_used_time)s, %(customer)s)
            RETURNING *
        """
        return self._insert(insert, vars(key))

    def get_key(self, key):
        select = """
            SELECT * FROM `keys`
             WHERE id=%s OR key=%s
        """
        return self._fetchone(select, (key, key))

    def get_keys(self, query=None):
        query = query or Query()
        select = """
            SELECT * FROM `keys`
            WHERE {where}
        """.format(where=query.where)
        return self._fetchall(select, query.vars)

    def update_key_last_used(self, key):
        update = """
            UPDATE `keys`
            SET last_used_time=%s, count=count+1
            WHERE id=%s OR key=%s
        """
        return self._update(update, (datetime.utcnow(), key, key))

    def delete_key(self, key):
        delete = """
            DELETE FROM `keys`
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

        customers = []
        for match in [login] + matches:
            select = """SELECT customer FROM customers WHERE match=%s"""
            response = self._fetchone(select, (match,))
            if response:
                customers.append(response.customer)

        if customers:
            if '*' in customers:
                return '*'  # all customers

            return customers

        raise NoCustomerMatch("No customer lookup configured for user '%s' or '%s'" % (login, ','.join(matches)))

    #### METRICS

    def get_metrics(self, type=None):
        select = """SELECT * FROM metrics"""
        if type:
            select += " WHERE type=%s"
        return self._fetchall(select, (type,))

    def set_gauge(self, gauge):
        upsert = """
            INSERT INTO metrics (`group`, name, title, description, value, type)
            VALUES ('%(group)s', '%(name)s', '%(title)s', '%(description)s', '%(value)s', '%(type)s')
            ON DUPLICATE KEY
            UPDATE value='%(value)s';
        """
        return self._upsert(upsert, vars(gauge))

    def inc_counter(self, counter):
        upsert = """
            INSERT INTO metrics (`group`, name, title, description, count, type)
            VALUES ('%(group)s', '%(name)s', '%(title)s', '%(description)s', '%(count)s', '%(type)s')
            ON DUPLICATE KEY
            UPDATE count=metrics.count+%(count)s;
        """
        return self._upsert(upsert, vars(counter))

    def update_timer(self, timer):
        upsert = """
            INSERT INTO metrics (`group`, name, title, description, count, total_time, type)
            VALUES ('%(group)s', '%(name)s', '%(title)s', '%(description)s', '%(count)s', '%(total_time)s', '%(type)s')
            ON DUPLICATE KEY
            UPDATE count=metrics.count+%(count)s, total_time=metrics.total_time+%(total_time)s;
        """
        data = vars(timer)
        self._upsert(upsert, data)

        get_query = "SELECT * from metrics where `group` = '%(group)s' AND name = '%(name)s' AND `type` = '%(type)s'" 
        
        metric_object = self._fetchone(get_query,data)
        print("Object: %s" % pprint.pformat(metric_object))
        metric = {}
        metric['group'] = metric_object[0]
        metric['name'] = metric_object[1]
        metric['title'] = metric_object[2]
        metric['description'] = metric_object[3]
        metric['value'] = metric_object[4]
        metric['count'] = metric_object[5]
        metric['total_time'] = metric_object[6]
        metric['type'] = metric_object[7]

        return metric_object

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

        # get list of alerts to be newly expired
        select = """
            SELECT id, event, last_receive_id
              FROM alerts
             WHERE status NOT IN ('expired','shelved') AND timeout!=0
               AND (last_receive_time + INTERVAL '1 second' * timeout) < (NOW() at time zone 'utc')
        """
        expired = self._fetchall(select, {})

        # get list of alerts to be unshelved
        select = """
        WITH shelved AS (
            SELECT DISTINCT ON (a.id) a.id, a.event, a.last_receive_id, h.update_time, a.timeout
              FROM alerts a, UNNEST(history) h
             WHERE a.status='shelved'
               AND h.type='action'
               AND h.status='shelved'
          ORDER BY a.id, h.update_time DESC
        )
        SELECT id, event, last_receive_id
          FROM shelved
         WHERE (update_time + INTERVAL '1 second' * timeout) < (NOW() at time zone 'utc')
        """
        unshelved = self._fetchall(select, {})

        return (expired, unshelved)

    #### SQL HELPERS

    def _insert(self, query, vars):
        """
        Insert, with return.
        """
        cursor = g.db.cursor()
        self._log(cursor, query, vars)
        print("Insert: %s" % (query % vars))
        cursor.execute(query % vars)
        g.db.commit()
        return cursor.fetchone()

    def _fetchone(self, query, vars=None, cursor_class=None):
        """
        Return none or one row.
        """
        cursor = g.db.cursor(named_tuple=True)
        if vars:
            print("Query: %s" % (query % vars))
            cursor.execute(query % vars)
        else:
            print("Query: %s" % query)
            cursor.execute(query)
        return cursor.fetchone()

    def _fetchall(self, query, vars, limit=None, offset=0):
        """
        Return multiple rows.
        """
        if limit is None:
            limit = current_app.config['DEFAULT_PAGE_SIZE']
        query += " LIMIT %s OFFSET %s""" % (limit, offset)
        cursor = g.db.cursor(named_tuple=True)
        #self._log(cursor, query, vars)
        print("Fetch all Query: %s" % (query % vars))
        cursor.execute(query % vars)
        return cursor.fetchall()

    def _update(self, query, vars, returning=False):
        """
        Update, with optional return.
        """
        cursor = g.db.cursor()
        #self._log(cursor, query, vars)
        print("Query: %s" % (query % vars))
        cursor.execute(query % vars)
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
        #self._log(cursor, query, vars)
        print("Query: %s" % (query % vars))
        cursor.execute(query % vars)
        g.db.commit()
        return cursor.fetchone() if returning else None

    def _log(self, cursor, query, vars):
        LOG = current_app.logger
        if vars:
            LOG.debug('{stars}\n{query}\n{stars}'.format(stars='*'*40, query=(query % vars)))
        else:
            LOG.debug('{stars}\n{query}\n{stars}'.format(stars='*'*40, query=query))

