#!/usr/bin/env python
########################################
#
# alert-syslog.py - Alert Syslog Receiver
#
########################################

import os
import sys
try:
    import json
except ImportError:
    import simplejson as json
import yaml
import stomp
import time
import datetime
import logging
import socket
import select
import uuid
import re
import fnmatch

__program__ = 'alert-syslog'
__version__ = '1.1.5'

BROKER_LIST  = [('localhost', 61613)] # list of brokers for failover
ALERT_QUEUE  = '/queue/alerts'

DEFAULT_TIMEOUT = 86400
EXPIRATION_TIME = 600 # seconds = 10 minutes

LOGFILE = '/var/log/alerta/alert-syslog.log'
PIDFILE = '/var/run/alerta/alert-syslog.pid'
DISABLE = '/opt/alerta/conf/alert-syslog.disable'
SYSLOGCONF = '/opt/alerta/conf/alert-syslog.yaml'
PARSERDIR = '/opt/alerta/bin/parsers'

SEVERITY_CODE = {
    # ITU RFC5674 -> Syslog RFC5424
    'CRITICAL':       1, # Alert
    'MAJOR':          2, # Crtical
    'MINOR':          3, # Error
    'WARNING':        4, # Warning
    'NORMAL':         5, # Notice
    'INFORM':         6, # Informational
    'DEBUG':          7, # Debug
}

SYSLOG_FACILITY_NAMES = [
    "kern",
    "user",
    "mail",
    "daemon",
    "auth",
    "syslog",
    "lpr",
    "news",
    "uucp",
    "cron",
    "authpriv",
    "ftp",
    "ntp",
    "audit",
    "alert",
    "clock",
    "local0",
    "local1",
    "local2",
    "local3",
    "local4",
    "local5",
    "local6",
    "local7"
]

SYSLOG_SEVERITY_NAMES = [
    "emerg",
    "alert",
    "crit",
    "err",
    "warning",
    "notice",
    "info",
    "debug"
]

SYSLOG_SEVERITY_MAP = {
    'emerg':   'CRITICAL',
    'alert':   'CRITICAL',
    'crit':    'MAJOR',
    'err':     'MINOR',
    'warning': 'WARNING',
    'notice':  'NORMAL',
    'info':    'INFORM',
    'debug':   'DEBUG',
}

SYSLOG_UDP_PORT             = 514
SYSLOG_TCP_PORT             = 514

def send_syslog(data):
    global conn

    if re.match('<\d+>1', data):
        # Parse RFC 5424 compliant message
        m = re.match(r'<(\d+)>1 (\S+) (\S+) (\S+) (\S+) (\S+) (.*)', data)
        if m:
            PRI = int(m.group(1))
            ISOTIMESTAMP = m.group(2)
            LOGHOST = m.group(3)
            APPNAME = m.group(4)
            PROCID = m.group(5)
            MSGID = m.group(6)
            TAG = '%s[%s] %s' % (APPNAME, PROCID, MSGID)
            MSG = m.group(7) 
            logging.info("Parsed RFC 5424 message OK")
        else:
            logging.error("Could not parse syslog RFC 5424 message: %s", data)
            return

    else:
        # Parse RFC 3164 compliant message
        m = re.match(r'<(\d+)>(\S{3})\s+(\d+) (\d+:\d+:\d+) (\S+) (\S+): (.*)', data)
        if m:
            PRI = int(m.group(1))
            LOGHOST = m.group(5)
            TAG = m.group(6)
            MSG = m.group(7)
            logging.info("Parsed RFC 3164 message OK")
        else:
            logging.error("Could not parse syslog RFC 3164 message: %s", data)
            return

    # Decode syslog PRI
    facility = PRI >> 3
    facility = SYSLOG_FACILITY_NAMES[facility]
    level = PRI & 7
    level = SYSLOG_SEVERITY_NAMES[level]

    # Defaults
    event       = '%s%s' % (facility.capitalize(), level.capitalize())
    resource    = LOGHOST
    severity    = SYSLOG_SEVERITY_MAP[level]
    group       = 'Syslog'
    value       = TAG
    text        = MSG
    environment = ['INFRA']
    service     = ['Infrastructure']
    tags        = [ '%s.%s' % (facility, level) ]
    correlate   = list()
    threshold   = ''

    try:
        syslogconf = yaml.load(open(SYSLOGCONF))
    except Exception, e:
        logging.warning('Failed to load Syslog configuration: %s. Using defaults.', e)
        syslogconf = dict()
    logging.info('Loaded %d Syslog configurations OK', len(syslogconf))

    for s in syslogconf:
        logging.debug('syslogconf: %s', s)
        if fnmatch.fnmatch('%s.%s' % (facility, level), s['priority']):
            if 'parser' in s:
                print 'Loading parser %s' % s['parser']
                try:
                    exec(open('%s/%s.py' % (PARSERDIR, s['parser'])))
                    logging.info('Parser %s/%s exec OK', PARSERDIR, s['parser'])
                except Exception, e:
                    print 'Parser %s failed: %s' % (s['parser'], e)
                    logging.warning('Parser %s failed', s['parser'])
            if 'event' in s:
                event = s['event']
            if 'resource' in s:
                resource = s['resource']
            if 'severity' in s:
                severity = s['severity']
            if 'group' in s:
                group = s['group']
            if 'value' in s:
                value = s['value']
            if 'text' in s:
                text = s['text']
            if 'environment' in s:
                environment = [s['environment']]
            if 'service' in s:
                service = [s['service']]
            if 'tags' in s:
                tags = s['tags']
            if 'correlatedEvents' in s:
                correlate = s['correlatedEvents']
            if 'thresholdInfo' in s:
                threshold = s['thresholdInfo']
            break

    alertid = str(uuid.uuid4()) # random UUID
    createTime = datetime.datetime.utcnow()

    headers = dict()
    headers['type']           = "syslogAlert"
    headers['correlation-id'] = alertid

    alert = dict()
    alert['id']               = alertid
    alert['resource']         = resource
    alert['event']            = event
    alert['group']            = group
    alert['value']            = value
    alert['severity']         = severity.upper()
    alert['severityCode']     = SEVERITY_CODE[alert['severity']]
    alert['environment']      = environment
    alert['service']          = service
    alert['text']             = text
    alert['type']             = 'syslogAlert'
    alert['tags']             = tags
    alert['summary']          = '%s - %s %s is %s on %s %s' % (','.join(environment), severity.upper(), event, value, ','.join(service), resource)
    alert['createTime']       = createTime.replace(microsecond=0).isoformat() + ".%03dZ" % (createTime.microsecond//1000)
    alert['origin']           = "%s/%s" % (__program__, os.uname()[1])
    alert['thresholdInfo']    = threshold
    alert['timeout']          = DEFAULT_TIMEOUT
    alert['correlatedEvents'] = correlate

    logging.info('%s : %s', alertid, json.dumps(alert))

    while not conn.is_connected():
        logging.warning('Waiting for message broker to become available')
        time.sleep(1.0)

    try:
        conn.send(json.dumps(alert), headers, destination=ALERT_QUEUE)
        broker = conn.get_host_and_port()
        logging.info('%s : Alert sent to %s:%s', alertid, broker[0], str(broker[1]))
    except Exception, e:
        logging.error('Failed to send alert to broker %s', e)

    return

class MessageHandler(object):

    def on_error(self, headers, body):
        logging.error('Received an error %s', body)

    def on_disconnected(self):
        global conn

        logging.warning('Connection lost. Attempting auto-reconnect to %s', ALERT_QUEUE)
        conn.start()
        conn.connect(wait=True)
        conn.subscribe(destination=ALERT_QUEUE, ack='auto')

def send_heartbeat():
    global conn

    heartbeatid = str(uuid.uuid4()) # random UUID
    createTime = datetime.datetime.utcnow()

    headers = dict()
    headers['type']           = "heartbeat"
    headers['correlation-id'] = heartbeatid
    # headers['persistent']     = 'false'
    # headers['expires']        = int(time.time() * 1000) + EXPIRATION_TIME * 1000

    heartbeat = dict()
    heartbeat['id']         = heartbeatid
    heartbeat['type']       = "heartbeat"
    heartbeat['createTime'] = createTime.replace(microsecond=0).isoformat() + ".%03dZ" % (createTime.microsecond//1000)
    heartbeat['origin']     = "%s/%s" % (__program__,os.uname()[1])
    heartbeat['version']    = __version__

    try:
        conn.send(json.dumps(heartbeat), headers, destination=ALERT_QUEUE)
        broker = conn.get_host_and_port()
        logging.info('%s : Heartbeat sent to %s:%s', heartbeatid, broker[0], str(broker[1]))
    except Exception, e:
        logging.error('Failed to send heartbeat to broker %s', e)

def main():
    global conn

    logging.basicConfig(level=logging.INFO, format="%(asctime)s alert-syslog[%(process)d] %(levelname)s - %(message)s", filename=LOGFILE)
    logging.info('Starting up Alert Syslog version %s', __version__)

    # Write pid file if not already running
    if os.path.isfile(PIDFILE):
        pid = open(PIDFILE).read()
        try:
            os.kill(int(pid), 0)
            logging.error('Process with pid %s already exists, exiting', pid)
            sys.exit(1)
        except OSError:
            pass
    file(PIDFILE, 'w').write(str(os.getpid()))

    while os.path.isfile(DISABLE):
        logging.warning('Disable flag exists (%s). Sleeping...', DISABLE)
        time.sleep(120)

    # Set up syslog UDP listener
    try:
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp.bind(('', SYSLOG_UDP_PORT))
    except socket.error, e:
        logging.error('Syslog UDP error: %s', e)
        sys.exit(2)
    logging.info('Listening on syslog port 514/udp')

    # Set up syslog TCP listener
    try:
        tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        tcp.bind(('', SYSLOG_TCP_PORT))
        tcp.listen(5)
    except socket.error, e:
        logging.error('Syslog TCP error: %s', e)
        sys.exit(2)
    logging.info('Listening on syslog port 514/tcp')

    # Connect to message broker
    try:
        conn = stomp.Connection(
                   BROKER_LIST,
                   reconnect_sleep_increase = 5.0,
                   reconnect_sleep_max = 120.0,
                   reconnect_attempts_max = 20
               )
        conn.set_listener('', MessageHandler())
        conn.start()
        conn.connect(wait=True)
    except Exception, e:
        logging.error('Stomp connection error: %s', e)

    while True:
        try:
            ip, op, rdy = select.select([udp,tcp], [], [])
            for i in ip:
                if i == udp:
                    data = udp.recv(4096)
                    logging.debug('Syslog UDP: %s', data)
                    send_syslog(data)
                if i == tcp:
                    client,addr = tcp.accept()
                    data = client.recv(4096)
                    client.close()
                    logging.debug('Syslog TCP: %s', data)
                    send_syslog(data)

            send_heartbeat()
            time.sleep(0.01)
        except (KeyboardInterrupt, SystemExit):
            conn.disconnect()
            os.unlink(PIDFILE)
            sys.exit(0)

if __name__ == '__main__':
    main()
