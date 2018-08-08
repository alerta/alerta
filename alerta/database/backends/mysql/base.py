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
import decimal

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

class DecimalEncoder(json.JSONEncoder):
    def decode(self,s):
        return s.decode()

    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return int(o)
        return super(DecimalEncoder, self).default(o)

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
        #print(command)
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

    def pre_process_alert(self, alert_tuple, histories, services, tags, correlates):
        alert_dict = alert_tuple._asdict()
        alert_dict['id'] = alert_dict['id'].encode('ascii','ignore')
        alert_dict['group'] = alert_dict['group'].encode('ascii','ignore')
        alert_dict['origin'] = alert_dict['origin'].encode('ascii','ignore')
        alert_dict['previousSeverity'] = alert_dict['previous_severity'].encode('ascii','ignore')
        alert_dict['trendIndication'] = alert_dict['trend_indication'].encode('ascii','ignore')
        alert_dict['receiveTime'] = alert_dict['receive_time']
        alert_dict['lastReceiveId'] = alert_dict['last_receive_id']
        alert_dict['lastReceiveTime'] = alert_dict['last_receive_time']

        alert_dict['rawData'] = alert_dict['raw_data'].encode('ascii','ignore') if alert_dict['raw_data'] else alert_dict['raw_data']
        alert_dict['status'] = alert_dict['status'].encode('ascii','ignore')
        alert_dict['duplicateCount'] = alert_dict['duplicate_count']
        alert_dict['attributes'] = json.loads(alert_dict['attributes'])
        alert_dict['repeat'] = True if alert_dict['repeat'] == 1 else False

        history_list = []
        for history in histories:
            hist_json = history._asdict()['history']
            #print("History: %s" % str(hist_json))
            history_list.append(json.loads(hist_json))
        alert_dict['history'] = history_list

        service_list = []
        for service in services:
            service_str = service._asdict()['service']
            #print("Service: %s" % str(service_str))
            service_list.append(service_str)
        alert_dict['service'] = service_list

        correlate_list = []
        for correlate in correlates:
            correlate_str = correlate._asdict()['correlate']
            #print("Correlate: %s" % str(correlate_str))
            correlate_list.append(correlate)
        alert_dict['correlate'] = correlate_list

        tag_list = []
        for tag in tags:
            tag_str = tag._asdict()['tag']
            #print("Tag: %s" % str(tag_str))
            tag_list.append(tag_str)
        alert_dict['tags'] = tag_list

        return alert_dict

   

    def get_severity(self, alert):
        print("--> get_severity")
        select = """
            SELECT severity FROM alerts
             WHERE environment='%(environment)s' AND resource='%(resource)s'
               AND ((event='%(event)s' AND severity!='%(severity)s')
                OR (event!='%(event)s' AND EXISTS (SELECT * FROM alert_correlate WHERE correlate = '%(event)s' AND alert_correlate.id = alerts.id)))
               AND {customer}
            """.format(customer="customer='%(customer)s'" if alert.customer else "customer IS NULL")
        return self._fetchone(select, vars(alert)).severity

    def get_status(self, alert):
        print("--> get_status")
        select = """
            SELECT status FROM alerts
             WHERE environment='%(environment)s' AND resource='%(resource)s'
              AND (event='%(event)s' OR EXISTS (SELECT * FROM alert_correlate WHERE correlate = '%(event)s' AND alert_correlate.id = alerts.id))
              AND {customer}
            """.format(customer="customer=%(customer)s" if alert.customer else "customer IS NULL")
        return self._fetchone(select, vars(alert)).status

    def get_status_and_value(self, alert):
        print("--> get_status_and_value")

        print("Alert customer: %s" % type(alert.customer))
        select = """
            SELECT status, value FROM alerts
             WHERE environment='%(environment)s' AND resource='%(resource)s'
              AND (event='%(event)s' OR EXISTS (SELECT * FROM alert_correlate WHERE correlate = '%(event)s' AND alert_correlate.id = alerts.id))
              AND {customer}
            """.format(customer="customer='%(customer)s'" if alert.customer else "customer IS NULL")
        r = self._fetchone(select, vars(alert))
        return r.status, r.value

    def is_duplicate(self, alert):
        print("--> is_duplicate")
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
        print("--> is_correlated")
        select = """
            SELECT id FROM alerts
             WHERE environment='%(environment)s' AND resource='%(resource)s'
               AND ((event='%(event)s' AND severity!='%(severity)s')
                OR (event!='%(event)s' AND EXISTS (SELECT * FROM alert_correlate WHERE correlate = '%(event)s' AND alert_correlate.id = alerts.id)))
               AND {customer}
        """.format(customer="customer='%(customer)s'" if alert.customer else "customer IS NULL")
        return bool(self._fetchone(select, vars(alert)))

    def is_flapping(self, alert, window=1800, count=2):
        print("--> is_flapping")
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

    def get_alert_aux(self, id, table, limit = None, orderby=None):
        data = {"id":id, "table":table}
        if limit:
            get_history = """SELECT * FROM `%(table)s` WHERE id = '%(id)s' LIMIT %d""" % limit    
        else:
            get_history = """SELECT * FROM `%(table)s` WHERE id = '%(id)s'"""

        if orderby:
            get_history += " %s" % orderby

        history = self._fetchall(get_history,data)

        return history

    def insert_alert_aux(self, id, table, column, data):
        insert_history = "INSERT IGNORE INTO `%s` (id, %s) VALUES ('%s', '%s');"

        if data:
            if type(data) == list:
                if len(data) > 0:
                    insert = None
                    insert = "INSERT IGNORE INTO `%s` (id, %s) VALUES " % (table,column)
                    for d in data:
                        if type(d) == History:
                            insert += "('%s','%s')," % (id, json.dumps(d, cls=HistoryEncoder))
                        if type(d) == str or type(d) == unicode:
                            insert += "('%s','%s')," % (id, d)
                    self._insert((insert.rstrip(',') + ";").replace("''","'"))
            elif type(data) == History:
                insert = insert_history % (table, column, id, json.dumps(data, cls=HistoryEncoder))
                self._insert(insert_history ,(table, column, id, json.dumps(data, cls=HistoryEncoder)))
            elif type(data) == str or type(data) == unicode:
                insert = insert_history % (table, column, id, data.replace("'",""))
                self._insert(insert_history, (table, column, id, data.replace("'","")))
            else:
                print("Wrong object")
                raise(Exception("Wrong object type %s" % str(type(data))))

    def dedup_alert(self, alert, history):
        print("--> dedup_alert")
        """
        Update alert value, text and rawData, increment duplicate count and set repeat=True, and
        keep track of last receive id and time but don't append to history unless status changes.
        """
        update = """UPDATE alerts
               SET status='%(status)s', value={value}, text='%(text)s', timeout=%(timeout)s, raw_data={raw_data}, `repeat`=%(repeat)s,
                   last_receive_id='%(last_receive_id)s', last_receive_time='%(last_receive_time)s', attributes=JSON_MERGE(attributes ,'%(attributes)s'),
                   duplicate_count=duplicate_count+1 
             WHERE environment='%(environment)s' AND resource='%(resource)s'
               AND event='%(event)s' AND severity='%(severity)s'
               AND {customer} ;
        """.format(limit=current_app.config['HISTORY_LIMIT'], 
                customer="customer='%(customer)s'" if alert.customer and alert.customer != 'None' else "customer IS NULL",
                value="'%(value)s'" if alert.value else "NULL",
                raw_data="'%(raw_data)s'" if alert.raw_data else "NULL")

        #print("History Type: %s" % type(alert.history))
        data = vars(alert)
        data['repeat'] = 1 if json.dumps(data['repeat'], cls=HistoryEncoder) == 'false' else 0 
        data['attributes'] = json.dumps(data['attributes'], cls=HistoryEncoder)

        get_query = '''SELECT * FROM alerts WHERE environment='%(environment)s'
               AND resource='%(resource)s'
               AND event='%(event)s'
               AND severity='%(severity)s'
               AND {customer}'''.format(limit=current_app.config['HISTORY_LIMIT'], customer="customer='%(customer)s'" if alert.customer and not alert.customer == 'None'  else "customer IS NULL",
                    value="'%(value)s'" if alert.value else "NULL",raw_data="'%(raw_data)s'" if alert.raw_data else "NULL",
                    history=", history=JSON_ARRAY_APPEND(history,'$','%(history)s')" if alert.history else "")

        self._update(update, data)
        
        alert_tuple = self._fetchone(get_query,data)
        alert_dict = None
        if alert_tuple:
            self.insert_alert_aux(alert_tuple.id, 'alert_history', 'history', history)
            #self.insert_alert_aux(alert_tuple.id, 'alert_service', 'service', data['service'])
            self.insert_alert_aux(alert_tuple.id, 'alert_tag', 'tag', data['tags'])
            #self.insert_alert_aux(alert_tuple.id, 'alert_correlate', 'correlate', data['correlate']) 
            
            histories = self.get_alert_aux(alert_tuple.id, 'alert_history')  
            services = self.get_alert_aux(alert_tuple.id, 'alert_service')
            tags = self.get_alert_aux(alert_tuple.id, 'alert_tag')
            correlates = self.get_alert_aux(alert_tuple.id, 'alert_correlate')

            alert_dict = self.pre_process_alert(alert_tuple, histories, services, tags, correlates)

        return alert_dict

    def correlate_alert(self, alert, history):
        print("--> correlate_alert")
        update = """UPDATE alerts
               SET event='%(event)s', severity='%(severity)s', status='%(status)s', value={value}, text='%(text)s',
                   create_time='%(create_time)s', timeout='%(timeout)s', raw_data={raw_data}, duplicate_count=%(duplicate_count)s,
                   `repeat`=%(repeat)s, previous_severity='%(previous_severity)s', trend_indication='%(trend_indication)s',
                   receive_time='%(receive_time)s', last_receive_id='%(last_receive_id)s',
                   last_receive_time='%(last_receive_time)s',
                   attributes=JSON_MERGE(attributes ,'%(attributes)s') 
             WHERE environment='%(environment)s' AND resource='%(resource)s'
               AND ((event='%(event)s' AND severity!='%(severity)s')
                    OR (event!='%(event)s' AND EXISTS (SELECT * FROM alert_correlate WHERE correlate = '%(event)s' AND alert_correlate.id = alerts.id)) 
                    )
               AND {customer} ;
        """.format(limit=current_app.config['HISTORY_LIMIT'], 
                customer="customer='%(customer)s'" if alert.customer and alert.customer != 'None' else "customer IS NULL",
                value="'%(value)s'" if alert.value else "NULL",
                raw_data="'%(raw_data)s'" if alert.raw_data else "NULL")
        
        data = vars(alert)
        data['repeat'] = 1 if json.dumps(data['repeat'], cls=HistoryEncoder) == 'false' else 0 
        data['attributes'] = json.dumps(data['attributes'], cls=HistoryEncoder)

        get_query = '''SELECT * FROM alerts 
            WHERE environment='%(environment)s' AND resource='%(resource)s'
               AND (event='%(event)s' AND severity='%(severity)s')
               AND {customer}
        '''.format(limit=current_app.config['HISTORY_LIMIT'], 
                customer="customer='%(customer)s'" if alert.customer else "customer IS NULL",
                value="'%(value)s'" if alert.value else "NULL",
                raw_data="'%(raw_data)s'" if alert.raw_data else "NULL")

        self._update(update, data)

        alert_tuple = self._fetchone(get_query, data)
        alert_dict = None
        if alert_tuple:
            self.insert_alert_aux(alert_tuple.id, 'alert_history', 'history', history)
            #self.insert_alert_aux(alert_tuple.id, 'alert_service', 'service', data['service'])
            self.insert_alert_aux(alert_tuple.id, 'alert_tag', 'tag', data['tags'])
            #self.insert_alert_aux(alert_tuple.id, 'alert_correlate', 'correlate', data['correlate']) 
            
            histories = self.get_alert_aux(alert_tuple.id, 'alert_history')  
            services = self.get_alert_aux(alert_tuple.id, 'alert_service')
            tags = self.get_alert_aux(alert_tuple.id, 'alert_tag')
            correlates = self.get_alert_aux(alert_tuple.id, 'alert_correlate')
            alert_dict = self.pre_process_alert(alert_tuple, histories, services, tags, correlates)
        
        return alert_dict


    def create_alert(self, alert):
        print("--> create_alert")

        insert = """
            INSERT INTO alerts (id, resource, event, environment, severity, status, `group`,
                value, `text`, attributes, origin, type, create_time, timeout, raw_data, customer,
                duplicate_count, `repeat`, previous_severity, trend_indication, receive_time, last_receive_id,
                last_receive_time)
            VALUES ('%(id)s', '%(resource)s', '%(event)s', '%(environment)s', '%(severity)s', '%(status)s',
                '%(group)s', {value}, '%(text)s', '%(attributes)s', '%(origin)s',
                '%(event_type)s', '%(create_time)s', '%(timeout)s', {raw_data}, {customer}, '%(duplicate_count)s',
                '%(repeat)s', '%(previous_severity)s', '%(trend_indication)s', '%(receive_time)s', '%(last_receive_id)s',
                '%(last_receive_time)s') ;
        """.format(customer="customer='%(customer)s'" if alert.customer and not alert.customer == 'None' else "NULL",
            value="'%(value)s'" if alert.value else "NULL",
            raw_data="'%(raw_data)s'" if alert.raw_data else "NULL")
        
        print("Tags Type: %s" % alert.tags)
        data = vars(alert)
        #data['origin'] = json.dumps(data['origin'], cls=HistoryEncoder)
        data['repeat'] = 1 if json.dumps(data['repeat'], cls=HistoryEncoder) == 'false' else 0 
        data['attributes'] = json.dumps(data['attributes'], cls=HistoryEncoder)
        #data['service'] = json.dumps(data['service'], cls=HistoryEncoder)
        #data['correlate'] = json.dumps(data['correlate'], cls=HistoryEncoder)
        #data['history'] = json.dumps(data['history'], cls=HistoryEncoder)
        #print(data['tags'])
        #data['tags'] = json.dumps(data['tags'], cls=HistoryEncoder)

        #print("Alert DATA: %s" % pprint.pformat(data))
        get_query = "select * from alerts where id = '%(id)s'" 
        self._insert(insert, data)

        alert_tuple = self._fetchone(get_query,data)

        self.insert_alert_aux(alert_tuple.id, 'alert_history', 'history', data['history'])
        self.insert_alert_aux(alert_tuple.id, 'alert_service', 'service', data['service'])
        self.insert_alert_aux(alert_tuple.id, 'alert_tag', 'tag', data['tags'])
        self.insert_alert_aux(alert_tuple.id, 'alert_correlate', 'correlate', data['correlate']) 

        histories = self.get_alert_aux(alert_tuple.id, 'alert_history')  
        services = self.get_alert_aux(alert_tuple.id, 'alert_service')
        tags = self.get_alert_aux(alert_tuple.id, 'alert_tag')
        correlates = self.get_alert_aux(alert_tuple.id, 'alert_correlate')

        return self.pre_process_alert(alert_tuple, histories, services, tags, correlates)

    def get_alert(self, id, customers=None):
        print("--> get_alert")
        select = """
            SELECT * FROM alerts
             WHERE (id REGEXP ('%(id)s') OR last_receive_id REGEXP ('%(id)s'))
               AND {customer}
        """.format(customer="customer IN ('%(customers)s')" if customers else "1=1")
        #return self._fetchone(select, {'id': id, 'customers': customers})
        select = select % {"id":id,"customers":customers}
        alert_tuple= self._fetchone(select)

        histories = self.get_alert_aux(id, 'alert_history')  
        services = self.get_alert_aux(id, 'alert_service')
        tags = self.get_alert_aux(id, 'alert_tag', orderby='ORDER BY `alert_tag_id` ASC')
        correlates = self.get_alert_aux(id, 'alert_correlate')

        alert_dict = None
        if alert_tuple:   
            alert_dict = self.pre_process_alert(alert_tuple, histories, services, tags, correlates)
        return alert_dict

    #### STATUS, TAGS, ATTRIBUTES

    def set_status(self, id, status, timeout, history=None):
        print("--> set_status")

        update = """
            UPDATE alerts
            SET status='%(status)s' {timeout}
            WHERE id REGEXP '%(id)s'
        """.format(limit=current_app.config['HISTORY_LIMIT'],
            timeout=', timeout=%(timeout)s' if timeout else "")
        data = {'id': id, 'like_id': id + '%', 'status': status, 'timeout': timeout}
        #return self._update(update, data, returning=True)
        get_query = "select * from alerts where id = '%(id)s'" 
        self._update(update, data, returning=True)
        alert_tuple = self._fetchone(get_query,data)

        histories = self.get_alert_aux(id, 'alert_history')  
        services = self.get_alert_aux(id, 'alert_service')
        tags = self.get_alert_aux(id, 'alert_tag')
        correlates = self.get_alert_aux(id, 'alert_correlate')

        alert_dict = self.pre_process_alert(alert_tuple, histories, services, tags, correlates)
        return alert_dict

    def set_severity_and_status(self, id, severity, status, timeout, history=None):
        print("--> set_severity_and_status")

        update = """
            UPDATE alerts
            SET severity='%(severity)s', status='%(status)s' {timeout} 
            WHERE id REGEXP '%(id)s' 
        """.format(limit=current_app.config['HISTORY_LIMIT'],
            timeout=', timeout=%(timeout)s' if timeout else "")

        data = {'id': id, 'like_id': id + '%', 'status': status, 'timeout': timeout, 'severity':severity}
        #return self._update(update, data, returning=True)
        get_query = "select * from alerts where id = '%(id)s'" 
        self._update(update, data, returning=True)
        alert_tuple = self._fetchone(get_query,data)

        histories = self.get_alert_aux(id, 'alert_history')  
        services = self.get_alert_aux(id, 'alert_service')
        tags = self.get_alert_aux(id, 'alert_tag')
        correlates = self.get_alert_aux(id, 'alert_correlate')
   
        alert_dict = self.pre_process_alert(alert_tuple, histories,services, tags, correlates)
        return alert_dict 

    def tag_alert(self, id, tags):
        print("--> tag_alert")

        self.insert_alert_aux(id, 'alert_tag', 'tag', tags)

        select = """SELECT * FROM alerts WHERE id REGEXP '%(id)s'"""
        alert_tuple = self._fetchone(select,{"id":id})

        histories = self.get_alert_aux(id, 'alert_history')  
        services = self.get_alert_aux(id, 'alert_service')
        tags = self.get_alert_aux(id, 'alert_tag', orderby='ORDER BY `alert_tag_id` ASC')
        correlates = self.get_alert_aux(id, 'alert_correlate')

        alert_dict = self.pre_process_alert(alert_tuple, histories, services, tags, correlates)
        return alert_dict

    def untag_alert(self, id, tags):
        print("--> untag_alert")

        delete = """DELETE FROM alert_tag WHERE (id = '%(id)s' OR id REGEXP '%(like_id)s') AND (0=1 %(tags)s)"""

        tags_str = ''
        if type(tags) == list:
            for tag in tags:
                tags_str +=  " OR tag = '%s'" % tag
        else:
            tags_str +=  "OR tag = '%s'" % tags

        data = {'id': id, 'like_id': id, 'tags': tags_str}

        select = """SELECT * FROM alerts WHERE id REGEXP '%(id)s'"""

        alert_tuple = self._fetchone(select,data)

        histories = self.get_alert_aux(id, 'alert_history')  
        services = self.get_alert_aux(id, 'alert_service')
        tags = self.get_alert_aux(id, 'alert_tag', orderby='ORDER BY `alert_tag_id` ASC')
        correlates = self.get_alert_aux(id, 'alert_correlate')

        self._delete(delete, data)

        alert_dict = self.pre_process_alert(alert_tuple, histories, services, tags, correlates)
        return alert_dict

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

        alert_tuple = self._fetchone(select,data)

        histories = self.get_alert_aux(id, 'alert_history')  
        services = self.get_alert_aux(id, 'alert_service')
        tags = self.get_alert_aux(id, 'alert_tag')
        correlates = self.get_alert_aux(id, 'alert_correlate')

        alert_dict = self.pre_process_alert(alert_tuple,histories,services,tags,correlates)
        return alert_dict

    def delete_alert(self, id):
        delete = """
            DELETE FROM alerts
            WHERE id REGEXP '%(id)s' 
        """
        data = {'id': id, 'like_id': id+'%'}
        select = """SELECT id FROM alerts WHERE id REGEXP '%(id)s'"""
        alert_object = self._fetchone(select,data)
        alert_object = alert_object._asdict()  

        self._delete(delete, data)
        return alert_object['id']

    #### SEARCH & HISTORY

    def get_alerts(self, query=None, page=None, page_size=None):
        query = query or Query()
        select = """
            SELECT * FROM alerts
            WHERE {where}
            ORDER BY {order}
        """.format(where=query.where, order=query.sort or 'last_receive_time')
        #raise Exception(str(select % query.vars))
        alerts_tuple = self._fetchall(select, query.vars, limit=page_size, offset=(page - 1) * page_size)
        #print("FetchAll Len: %d" % len(alerts))
        alerts_dict = []
        for alert_tuple in alerts_tuple:
            histories = self.get_alert_aux(alert_tuple.id, 'alert_history')  
            services = self.get_alert_aux(alert_tuple.id, 'alert_service')
            tags = self.get_alert_aux(alert_tuple.id, 'alert_tag')
            correlates = self.get_alert_aux(alert_tuple.id, 'alert_correlate')
            alert_dict = self.pre_process_alert(alert_tuple, histories, services, tags, correlates)
            alerts_dict.append(alert_dict)
        #for x in alerts:
        #   print("Pre alert: %s" % pprint.pformat(x))
        #for alert in alerts:
        #    alert = alert._asdict()
        #    self.pre_process_alert(alert)
        #print('GetAlerts Object: %s' % pprint.pformat(alerts[0]))
        return alerts_dict

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
                   environment AS environments, service AS services, JSON_OBJECTAGG(alerts.id,resource) as resources
              FROM alerts, service
             WHERE service.id = alerts.id AND {where}
          GROUP BY {group}
          ORDER BY count DESC
        """.format(where=query.where, group=group)

        rows = [t._asdict() for t in self._fetchall(select, query.vars, limit=topn)]

        returns = []

        for r in rows:
         #   r['resource'] =
            r['resources'] = json.loads(r['resources'])
            elem = {}
            elem['count'] = int(r['count'])
            elem['duplicateCount'] = int(r['duplicate_count'])
            elem['environments'] = r['environments']
            elem['services'] = r['services']
            elem["%s" % group] = r['event']
            elem["resources"] = []
            for t in r['resources'].keys():
                res ={}
                res['id'] = t
                res['resources'] = r['resources'][t]
                res['href'] = absolute_url('/alerts/%s' % t)
                elem["resources"].append(res)
                #print(res)

            returns.append(elem)

        #print(pprint.pformat(rows))

        return returns

    def get_topn_flapping(self, query=None, group="event", topn=10):
        query = query or Query()
        select = """
            SELECT topn.event, COUNT(1) as count, SUM(duplicate_count) AS duplicate_count,
                   environment AS environments, service AS services,
                   JSON_OBJECTAGG(topn.id,resource) as resources
              FROM (SELECT * FROM alerts WHERE {where}) as topn, history hist, service 
             WHERE topn.id = service.id AND JSON_EXTRACT(history, '$.type') ='severity'
          GROUP BY topn.{group}
          ORDER BY count DESC
        """.format(where=query.where, group=group)

        #select = """
        #    WITH topn AS (SELECT * FROM alerts WHERE {where})
        #    SELECT topn.event, COUNT(1) as count, SUM(duplicate_count) AS duplicate_count,
        #           array_agg(DISTINCT environment) AS environments, array_agg(DISTINCT svc) AS services,
        #           array_agg(DISTINCT ARRAY[topn.id, resource]) AS resources
        #      FROM topn, UNNEST (service) svc, history hist
        #     WHERE hist.type='severity' AND 
        #  GROUP BY topn.{group}
        #  ORDER BY count DESC
        #""".format(where=query.where, group=group)

        rows = [t._asdict() for t in self._fetchall(select, query.vars, limit=topn)]

        returns = []

        for r in rows:
         #   r['resource'] =
            r['resources'] = json.loads(r['resources'])
            elem = {}
            elem['count'] = int(r['count'])
            elem['duplicateCount'] = int(r['duplicate_count'])
            elem['environments'] = r['environments']
            elem['services'] = r['services']
            elem["%s" % group] = r['event']
            elem["resources"] = []
            for t in r['resources'].keys():
                res ={}
                res['id'] = t
                res['resources'] = r['resources'][t]
                res['href'] = absolute_url('/alerts/%s' % t)
                elem["resources"].append(res)
                #print(res)

            returns.append(elem)

        
        return returns

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
            SELECT environment, count(1)  count FROM alerts
            WHERE {where}
            GROUP BY environment
        """.format(where=query.where)
        return [{"environment": e.environment, "count": e.count} for e in self._fetchall(select, query.vars, limit=topn)]

    #### SERVICES

    def get_services(self, query=None, topn=100):
        query = query or Query()
        select = """
            SELECT environment, service svc, count(1) count FROM alerts, service
            WHERE {where}
            GROUP BY environment, service
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

    def pre_process_blackout(self, blackout_tuple, services, tags):
        blackout_dict = blackout_tuple._asdict()
        blackout_dict['id'] = blackout_dict['id'].encode('ascii','ignore')
        #blackout_dict['group'] = blackout_dict['group'].encode('ascii','ignore') if 
  
        service_list = []
        for service in services:
            service_str = service._asdict()['service']
            #print("Service: %s" % str(service_str))
            service_list.append(service_str)
        blackout_dict['service'] = service_list

        tag_list = []
        for tag in tags:
            tag_str = tag._asdict()['tag']
            #print("Tag: %s" % str(tag_str))
            tag_list.append(tag_str)
        blackout_dict['tags'] = tag_list

        return blackout_dict

    def get_blackout_aux(self, id, table, limit = None, orderby=None):
        data = {"id":id, "table":table}
        if limit:
            get_history = """SELECT * FROM `%(table)s` WHERE id = '%(id)s' LIMIT %d""" % limit    
        else:
            get_history = """SELECT * FROM `%(table)s` WHERE id = '%(id)s'"""

        if orderby:
            get_history += " %s" % orderby

        history = self._fetchall(get_history,data)

        return history

    def insert_blackout_aux(self, id, table, column, data):
        insert_history = "INSERT IGNORE INTO `%s` (id, %s) VALUES ('%s', '%s');"

        if data:
            if type(data) == list:
                if len(data) > 0:
                    insert = None
                    insert = "INSERT IGNORE INTO `%s` (id, %s) VALUES " % (table,column)
                    for d in data:
                        if type(d) == History:
                            insert += "('%s','%s')," % (id, json.dumps(d, cls=HistoryEncoder))
                        if type(d) == str or type(d) == unicode:
                            insert += "('%s','%s')," % (id, d)
                    self._insert(insert.rstrip(',') + ";")
            elif type(data) == History:
                insert = insert_history % (table, column, id, json.dumps(data, cls=HistoryEncoder))
                self._insert(insert_history ,(table, column, id, json.dumps(data, cls=HistoryEncoder)))
            elif type(data) == str or type(data) == unicode:
                insert = insert_history % (table, column, id, data)
                self._insert(insert_history, (table, column, id, data))
            else:
                print("Wrong object")
                raise(Exception("Wrong object type %s" % str(type(data))))

    def create_blackout(self, blackout):
        insert = """
            INSERT INTO blackouts (id, priority, environment, resource, event, `group`, customer, start_time, end_time, duration)
            VALUES ('%(id)s', '%(priority)s', '%(environment)s', %(resource)s, %(event)s, %(group)s, %(customer)s, '%(start_time)s', '%(end_time)s', '%(duration)s')
        """
        data = vars(blackout)
        #data['service'] = data['service'] if data['service'] else 'NULL';
        data['resource'] = data['resource'] if data['resource'] and not data['resource'] == 'None' else 'NULL';
        data['event'] = data['event'] if data['event'] and not data['event'] == 'None' else 'NULL';
        data['group'] = data['group'] if data['group'] and not data['group'] == 'None' else 'NULL';
        #print("%s %s" % (data['customer'], type(data['customer'])))
        data['customer'] = data['customer'] if data['customer'] and not data['customer'] == 'None' else 'NULL';
        
        self._insert(insert, data)
        get_query = "select * from `blackouts` where id = '%(id)s'"
        blackout_tuple = self._fetchone(get_query, data)

        self.insert_blackout_aux(blackout_tuple.id, 'blackout_service', 'service', data['service'])
        self.insert_blackout_aux(blackout_tuple.id, 'blackout_tag', 'tag', data['tags'])
  
        services = self.get_blackout_aux(blackout_tuple.id, 'blackout_service')
        tags = self.get_blackout_aux(blackout_tuple.id, 'blackout_tag')

        blackout_dict = self.pre_process_blackout(blackout_tuple,services,tags)

        return blackout_dict


    def get_blackout(self, id, customer=None):
        select = """
            SELECT * FROM blackouts
            WHERE id=%(id)s
              AND {customer}
        """.format(customer="customer='%(customer)s'" if customer else "1=1")
        blackout_tuple = self._fetchone(select, {'id': id, 'customer': customer})
        services = self.get_blackout_aux(blackout_tuple.id, 'blackout_service')
        tags = self.get_blackout_aux(blackout_tuple.id, 'blackout_tag')

        blackout_dict = self.pre_process_blackout(blackout_tuple,services,tags)

        return blackout_dict

    def get_blackouts(self, query=None):
        query = query or Query()
        select = """
            SELECT * FROM blackouts
            WHERE {where}
        """.format(where=query.where)
        #return self._fetchall(select, query.vars)

        blackouts_tuple = self._fetchall(select, query.vars)
        #print("FetchAll Len: %d" % len(alerts))
        blackout_dict = []
        for blackout_tuple in alerts_tuple:
            services = self.get_alert_aux(blackout_tuple.id, 'blackout_service')
            tags = self.get_alert_aux(blackout_tuple.id, 'blackout_tag')
            blackout_dict = self.pre_process_blackout(blackout_tuple, services, tags)
            blackout_dict.append(blackout_dict)
        #for x in alerts:
        #   print("Pre alert: %s" % pprint.pformat(x))
        #for alert in alerts:
        #    alert = alert._asdict()
        #    self.pre_process_alert(alert)
        #print('GetAlerts Object: %s' % pprint.pformat(alerts[0]))
        return blackout_dict

    def is_blackout_period(self, alert):
        now = datetime.utcnow()

        data = vars(alert)
        tags_str = ''
        for tag in data['tags']:
            tags_str += "'%s'," % tag
        tags_str = tags_str.rstrip(',')
        data['tags'] = tags_str

        services_str = ''
        for service in data['service']:
            services_str += "'%s'," % service
        services_str = services_str.rstrip(',')
        data['service'] = services_str
        #time.sleep(1)

        select = """SELECT * FROM blackouts WHERE start_time<='%(now)s' AND end_time>'%(now)s'
        AND environment='%(environment)s' AND (
            (resource IS NULL 
                AND NOT EXISTS (SELECT * FROM blackout_service WHERE blackout_service.id = blackouts.id) 
                AND event IS NULL 
                AND `group` IS NULL 
                AND NOT EXISTS (SELECT * FROM blackout_tag WHERE blackout_tag.id = blackouts.id)
            ) OR (resource='%(resource)s' 
                AND NOT EXISTS (SELECT * FROM blackout_service WHERE blackout_service.id = blackouts.id) 
                AND event IS NULL 
                AND `group` IS NULL 
                AND NOT EXISTS (SELECT * FROM blackout_tag WHERE blackout_tag.id = blackouts.id)
            ) OR (resource IS NULL 
                AND EXISTS (SELECT * FROM blackout_service WHERE blackout_service.id = blackouts.id 
                AND service in (%(service)s)) 
                AND event IS NULL 
                AND `group` IS NULL 
                AND NOT EXISTS (SELECT * FROM blackout_tag WHERE blackout_tag.id = blackouts.id)
            )
                
                
        )
        """.format(service_existence="AND EXISTS (SELECT * FROM blackout_service WHERE blackout_service.id = blackouts.id AND service in (%(service)s))" if len(services_str) > 0 else '')

        '''
        select = """SELECT *
            FROM blackouts
            WHERE start_time<='%(now)s' AND end_time>'%(now)s'
                AND environment='%(environment)s'
                AND (
                (resource IS NULL AND NOT EXISTS (SELECT * FROM blackout_service WHERE blackout_service.id = blackouts.id) AND event IS NULL AND `group` IS NULL AND NOT EXISTS (SELECT * FROM blackout_tag WHERE blackout_tag.id = blackouts.id))
                OR (resource='%(resource)s' AND NOT EXISTS (SELECT * FROM blackout_service WHERE blackout_service.id = blackouts.id) AND event IS NULL AND `group` IS NULL AND NOT EXISTS (SELECT * FROM blackout_tag WHERE blackout_tag.id = blackouts.id)) 
                
                OR (resource IS NULL AND EXISTS (SELECT * FROM blackout_service WHERE blackout_service.id = blackouts.id AND service in (%(service)s)) AND event IS NULL AND `group` IS NULL AND NOT EXISTS (SELECT * FROM blackout_tag WHERE blackout_tag.id = blackouts.id))
                OR (resource IS NULL AND NOT EXISTS (SELECT * FROM blackout_service WHERE blackout_service.id = blackouts.id) AND event='%(event)s' AND `group` IS NULL AND NOT EXISTS (SELECT * FROM blackout_tag WHERE blackout_tag.id = blackouts.id))
                OR (resource IS NULL AND NOT EXISTS (SELECT * FROM blackout_service WHERE blackout_service.id = blackouts.id) AND event IS NULL AND `group`='%(group)s' AND NOT EXISTS (SELECT * FROM blackout_tag WHERE blackout_tag.id = blackouts.id))
                OR (resource='%(resource)s' AND NOT EXISTS (SELECT * FROM blackout_service WHERE blackout_service.id = blackouts.id) AND event='%(event)s' AND `group` IS NULL AND NOT EXISTS (SELECT * FROM blackout_tag WHERE blackout_tag.id = blackouts.id))
                OR (resource IS NULL AND NOT EXISTS (SELECT * FROM blackout_service WHERE blackout_service.id = blackouts.id) AND event IS NULL AND `group` IS NULL AND EXISTS (SELECT * FROM blackout_tag WHERE blackout_tag.id = blackouts.id AND tag in (%(tags)s)))
                )
        """
        '''

        #print("QueryData: %s" % pprint.pformat(data))
        #data['service'] = json.dumps(data['service'])
        data['last_receive_time'] = json.dumps(data['last_receive_time'], cls=HistoryEncoder)
        data['history'] = json.dumps(data['history'], cls=HistoryEncoder)
        data['correlate'] = json.dumps(data['correlate'], cls=HistoryEncoder)
        #data['tags'] = json.dumps(data['tags'], cls=HistoryEncoder)
        data['now'] = now



        #if current_app.config['CUSTOMER_VIEWS']:
        #    select += " AND (customer IS NULL OR {customer})".format(customer="customer='%(customer)s'" if data['customer'] and data['customer'] != 'None' else ' 0=1')

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
            WHERE id REGXP %(id)s 
            RETURNING id
        """
        return self._delete(delete, {'id': id, 'like_id': id+'%'}, returning=True)

    #### API KEYS

    def create_key(self, key):
        insert = """
            INSERT INTO `keys` (id, `key`, `user`, scopes, text, expire_time, `count`, last_used_time, customer)
            VALUES ('%(id)s', '%(key)s', '%(user)s', '%(scopes)s', '%(text)s', '%(expire_time)s', %(count)s, %(last_used_time)s, '%(customer)s')
        """
        get_query = "select * from `keys` where id = '%(id)s'"
        data = vars(key)
        data['scopes'] = json.dumps(data['scopes'])
        if data['last_used_time'] is None:
            data['last_used_time'] = 'NULL'
        self._insert(insert, data)
        key = self._fetchone(get_query, data)
        return key

    def get_key(self, key):
        select = """
            SELECT * FROM `keys`
             WHERE id='%s' OR `key`='%s'
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
            SET last_used_time='%s', count=count+1
            WHERE id='%s' OR `key`='%s'
        """
        return self._update(update, (datetime.utcnow(), key, key))

    def delete_key(self, key):
        delete = """
            DELETE FROM `keys`
            WHERE `id`='%s' OR `key`='%s'
        """

        select = """SELECT id FROM `keys` WHERE id REGEXP '%s' OR `key`='%s'"""
        key_object = self._fetchone(select,(key, key))
        key_object = key_object._asdict()  

        self._delete(delete, (key, key))
        return key_object['id']

    #### USERS

    def create_user(self, user):
        insert = """
            INSERT INTO users (id, name, email, password, status, roles, attributes,
                create_time, last_login, text, update_time, email_verified)
            VALUES ('%(id)s', '%(name)s', '%(email)s', '%(password)s', '%(status)s', '%(roles)s', '%(attributes)s', '%(create_time)s',
                %(last_login)s, '%(text)s', '%(update_time)s', %(email_verified)s)
        """
        get_query = "SELECT * from users where id = '%(id)s'"
        data = vars(user)
        data['roles'] = json.dumps(data['roles'])
        data['attributes'] = json.dumps(data['attributes'])
        if data['last_login'] is None:
            data['last_login'] = 'NULL'
        self._insert(insert, data)
        user = self._fetchone(get_query, data)
        if user:
            user = user._asdict()
            user['roles'] = json.loads(user['roles'])
            user['attributes'] = json.loads(user['attributes'])
        return user

        return self._insert(insert, vars(user))

    def get_user(self, id):
        select = """SELECT * FROM users WHERE id='%s'"""
        user = self._fetchone(select, (id,))
        if user:
            user = user._asdict()
            user['roles'] = json.loads(user['roles'])
            user['attributes'] = json.loads(user['attributes'])
        return user

    def get_users(self, query=None):
        query = query or Query()
        select = """
            SELECT * FROM users
            WHERE {where}
        """.format(where=query.where)
        users = self._fetchall(select, query.vars)
        if users:
            for i in range(len(users)): 
                if users[i]:
                    users[i] = users[i]._asdict()
                    users[i]['roles'] = json.loads(users[i]['roles'])
                    users[i]['attributes'] = json.loads(users[i]['attributes'])
        return users

    def get_user_by_email(self, email):
        select = """SELECT * FROM users WHERE email='%s'"""
        user = self._fetchone(select, (email,))
        if user:
            user = user._asdict()
            user['roles'] = json.loads(user['roles'])
            user['attributes'] = json.loads(user['attributes'])
        return user

    def get_user_by_hash(self, hash):
        select = """SELECT * FROM users WHERE hash=%s"""
        return self._fetchone(select, (hash,))

    def update_last_login(self, id):
        update = """
            UPDATE users
            SET last_login='%s'
            WHERE id='%s'
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
            WHERE id='%s'
        """

        select = """SELECT id FROM `users` WHERE id REGEXP '%s'"""
        key_object = self._fetchone(select,(id,))
        key_object = key_object._asdict()  

        self._delete(delete, (id,))
        return key_object['id']

        #return self._delete(delete, (id,), returning=True)

    #### PERMISSIONS

    def create_perm(self, perm):
        insert = """
            INSERT INTO perms (id, match, scopes)
            VALUES ('%(id)s', %(match)s, %(scopes)s)
        """
        get_query = "select * from perms where id = '%(id)s'"
        data = vars(perm)
        data['scopes'] = json.dumps(data['scopes'])

        self._insert(insert, data)
        perm = self._fetchone(get_query, data)
        return perm

    def get_perm(self, id):
        select = """SELECT * FROM perms WHERE id=%s"""
        return self._fetchone(select, (id,))

    def get_perms(self, query=None):
        query = query or Query()
        select = """
            SELECT * FROM perms
            WHERE {where}
        """.format(where=query.where)
        perms = self._fetchall(select, query.vars)
        for perm in perms:
            perm['scopes'] = json.loads(perm['scopes'])
        return 

    def delete_perm(self, id):
        delete = """
            DELETE FROM perms
            WHERE id='%s'
        """
        select = """SELECT id FROM `perms` WHERE id = '%s'"""
        key_object = self._fetchone(select,(id,))
        key_object = key_object._asdict()  

        self._delete(delete, (id,))
        return key_object['id']

        #return self._delete(delete, (id,), returning=True)

    def get_scopes_by_match(self, login, matches):
        if login in current_app.config['ADMIN_USERS']:
            return ['admin', 'read', 'write']

        scopes = list()
        for match in matches:
            select = """SELECT scopes FROM perms WHERE `match`='%s'"""
            response = self._fetchone(select, (match,))
            if response:
                scopes.extend(response.scopes)
        return set(scopes) or current_app.config['USER_DEFAULT_SCOPES']

    #### CUSTOMERS

    def create_customer(self, customer):
        insert = """
            INSERT INTO customers (`id`, `match`, `customer`)
            VALUES ('%(id)s', '%(match)s', '%(customer)s')
        """
        get_query = "select * from customers where id = '%(id)s'"
        data = vars(customer)

        self._insert(insert, data)
        cust = self._fetchone(get_query, data)
        return cust

    def get_customer(self, id):
        select = """SELECT * FROM customers WHERE id='%s'"""
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
            WHERE id='%s'
        """
        select = """SELECT id FROM `customers` WHERE id = '%s'"""
        key_object = self._fetchone(select,(id,))
        key_object = key_object._asdict()  

        self._delete(delete, (id,))
        return key_object['id']

        #return self._delete(delete, (id,), returning=True)

    def get_customers_by_match(self, login, matches):
        if login in current_app.config['ADMIN_USERS']:
            return '*'  # all customers

        customers = []
        for match in [login] + matches:
            select = """SELECT customer FROM customers WHERE `match`='%s'"""
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

    def _insert(self, query, vars= None):
        """
        Insert, with return.
        """
        cursor = g.db.cursor()
        #self._log(cursor, query, vars)
        if vars:
            print("Insert: %s" % (query % vars))
            cursor.execute(query % vars)
        else:
            print("Insert: %s" % query)
            cursor.execute(query)
        g.db.commit()
        ret = cursor.fetchone()
        cursor.close()
        return ret

    def _insert_multiple(self, query, vars=None):
        """
        Insert, with return.
        """
        cursor = g.db.cursor()
        #self._log(cursor, query, vars)
        if vars:
            print("Insert: %s" % (query % vars))
            cursor.execute(query % vars, multi=True)
        else:
           # print("Insert: %s" % (query))
            cursor.execute(query, multi=True)
        g.db.commit()
        ret = cursor.fetchone()
        cursor.close()
        return ret

    def _fetchone(self, query, vars=None, cursor_class=None):
        """
        Return none or one row.
        """
        cursor = g.db.cursor(named_tuple=True, buffered=True)
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
        #print("Fetchall query: %s " % (query % vars))
        query += " LIMIT %s OFFSET %s""" % (limit, offset)
        cursor = g.db.cursor(named_tuple=True,buffered=True)
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

