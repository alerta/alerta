#!/usr/bin/env python
########################################
#
# alert-syslog.py - Alert Syslog Receiver
#
########################################

# TODO
# 1. parse SD PARAMS
# 2. add configurable parsing

import os
import sys
try:
    import json
except ImportError:
    import simplejson as json
import stomp
import time
import datetime
import logging
import socket
import select
import uuid
import re

__version__ = '1.0.1'

BROKER_LIST  = [('localhost', 61613)] # list of brokers for failover
ALERT_QUEUE  = '/queue/alerts'
EXPIRATION_TIME = 600 # seconds = 10 minutes

LOGFILE = '/var/log/alerta/alert-syslog.log'
PIDFILE = '/var/run/alerta/alert-syslog.pid'
DISABLE = '/opt/alerta/conf/alert-syslog.disable'

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
        m = re.match(r'<(\d+)>(\S{3}) (\d+) (\d+:\d+:\d+) (\S+) (\S+): (.*)', data)
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
    fac = PRI >> 3
    sev = PRI & 7
    facility = SYSLOG_FACILITY_NAMES[fac]
    severity = SYSLOG_SEVERITY_NAMES[sev]

    # Assign alert attributes
    environment = 'INFRA'
    service = 'Servers'
    resource =  LOGHOST
    event = '%s%s' % (facility.capitalize(), severity.capitalize())
    group = 'Syslog'
    value = TAG or MSGID
    text = MSG
    tags = [ '%s.%s' % (facility, severity) ]

    alertid = str(uuid.uuid4()) # random UUID
    createTime = datetime.datetime.utcnow()

    headers = dict()
    headers['type']           = "syslogAlert"
    headers['correlation-id'] = alertid
    headers['persistent']     = 'true'
    headers['expires']        = int(time.time() * 1000) + EXPIRATION_TIME * 1000

    alert = dict()
    alert['id']            = alertid
    alert['resource']      = (environment + '.' + service + '.' + resource).lower()
    alert['event']         = event
    alert['group']         = group
    alert['value']         = value
    alert['severity']      = SYSLOG_SEVERITY_MAP[severity]
    alert['severityCode']  = SEVERITY_CODE[alert['severity']]
    alert['environment']   = environment.upper()
    alert['service']       = service
    alert['text']          = text
    alert['type']          = 'syslogAlert'
    alert['tags']          = tags
    alert['summary']       = '%s - %s %s is %s on %s %s' % (environment, alert['severity'].upper(), event, value, service, resource)
    alert['createTime']    = createTime.replace(microsecond=0).isoformat() + ".%06dZ" % createTime.microsecond
    alert['origin']        = 'alert-syslog/%s' % os.uname()[1]
    alert['thresholdInfo'] = 'n/a'

    logging.info('%s : %s', alertid, json.dumps(alert))

    try:
        conn.send(json.dumps(alert), headers, destination=ALERT_QUEUE)
    except Exception, e:
        print >>sys.stderr, "ERROR: Failed to send alert to broker - %s " % e
        logging.error('Failed to send alert to broker %s', e)
        sys.exit(1)
    broker = conn.get_host_and_port()
    logging.info('%s : Alert sent to %s:%s', alertid, broker[0], str(broker[1]))

    return

def main():
    global conn

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s alert-syslog[%(process)d] %(levelname)s - %(message)s", filename=LOGFILE)
    logging.info('Starting up Alert Syslog version %s', __version__)

    # Write pid file
    if os.path.isfile(PIDFILE):
        logging.error('%s already exists, exiting', PIDFILE)
        sys.exit(1)
    else:
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
        tcp.bind(('', SYSLOG_TCP_PORT))
        tcp.listen(5)
    except socket.error, e:
        logging.error('Syslog TCP error: %s', e)
        sys.exit(2)
    logging.info('Listening on syslog port 514/tcp')

    # Connect to message broker
    try:
        conn = stomp.Connection(BROKER_LIST)
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

            time.sleep(0.01)
        except (KeyboardInterrupt, SystemExit):
            conn.disconnect()
            os.unlink(PIDFILE)
            sys.exit(0)

if __name__ == '__main__':
    main()
