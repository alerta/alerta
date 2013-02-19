
import os
import sys
import time
import datetime
import argparse
import uuid
import json
import socket
import select
import re
import fnmatch

import yaml
import kombu

from alerta.alert import severity, syslog

from alerta.common.daemon import Daemon


__program__ = 'alert-syslog'
__version__ = '1.1.7'


_DEFAULT_BROKER_LIST = [('localhost', 61613), ( '', 61613)]

BROKER_LIST  = [('localhost', 61613)] # list of brokers for failover
ALERT_QUEUE  = '/queue/alerts'

DEFAULT_TIMEOUT = 86400
EXPIRATION_TIME = 600 # seconds = 10 minutes

LOGFILE = '/var/log/alerta/alert-syslog.log'
PIDFILE = '/var/run/alerta/alert-syslog.pid'
DISABLE = '/opt/alerta/alerta/alert-syslog.disable'
SYSLOGCONF = '/opt/alerta/alerta/alert-syslog.yaml'
PARSERDIR = '/opt/alerta/bin/parsers'


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
            LOG.info("Parsed RFC 5424 message OK")
        else:
            LOG.error("Could not parse syslog RFC 5424 message: %s", data)
            return

    else:
        # Parse RFC 3164 compliant message
        m = re.match(r'<(\d+)>(\S{3})\s+(\d+) (\d+:\d+:\d+) (\S+) (\S+): (.*)', data)
        if m:
            PRI = int(m.group(1))
            LOGHOST = m.group(5)
            TAG = m.group(6)
            MSG = m.group(7)
            LOG.info("Parsed RFC 3164 message OK")
        else:
            LOG.error("Could not parse syslog RFC 3164 message: %s", data)
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
    suppress    = False

    try:
        syslogconf = yaml.load(open(SYSLOGCONF))
        LOG.info('Loaded %d Syslog configurations OK', len(syslogconf))
    except Exception, e:
        LOG.warning('Failed to load Syslog configuration: %s. Using defaults.', e)
        syslogconf = dict()

    for s in syslogconf:
        LOG.debug('syslogconf: %s', s)
        if fnmatch.fnmatch('%s.%s' % (facility, level), s['priority']):
            if 'parser' in s:
                LOG.debug('Loading parser %s', s['parser'])
                try:
                    exec(open('%s/%s.py' % (PARSERDIR, s['parser'])))
                    LOG.info('Parser %s/%s exec OK', PARSERDIR, s['parser'])
                except Exception, e:
                    LOG.warning('Parser %s failed: %s', s['parser'], e)
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
            if 'suppress' in s:
                suppress = s['suppress']
            break

    if suppress:
        LOG.info('Suppressing %s.%s syslog message from %s', facility, level, resource)
        return

    syslogAlert = Alert(resource, event, correlate, group, value, severity, environment,
                        service, text, 'syslogAlert', tags, 'what here???', 'n/a')
    syslogAlert.send()

    while not conn.is_connected():
        LOG.warning('Waiting for message broker to become available')
        time.sleep(1.0)

    try:
        conn.send(json.dumps(alert), headers, destination=ALERT_QUEUE)
        broker = conn.get_host_and_port()
        LOG.info('%s : Alert sent to %s:%s', alertid, broker[0], str(broker[1]))
    except Exception, e:
        LOG.error('Failed to send alert to broker %s', e)

    return

class MessageHandler(object):

    def on_error(self, headers, body):
        LOG.error('Received an error %s', body)

    def on_disconnected(self):
        global conn

        LOG.warning('Connection lost. Attempting auto-reconnect to %s', ALERT_QUEUE)
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
        LOG.info('%s : Heartbeat sent to %s:%s', heartbeatid, broker[0], str(broker[1]))
    except Exception, e:
        LOG.error('Failed to send heartbeat to broker %s', e)



def main():

    # TODO(nsatterl): if not --debug
    if True:
        daemon = Daemon(__program__)
        daemon.start()


    # Write pid file if not already running
    if os.path.isfile(PIDFILE):
        pid = open(PIDFILE).read()
        try:
            os.kill(int(pid), 0)
            LOG.error('Process with pid %s already exists, exiting', pid)
            sys.exit(1)
        except OSError:
            pass
    file(PIDFILE, 'w').write(str(os.getpid()))

    while os.path.isfile(DISABLE):
        LOG.warning('Disable flag exists (%s). Sleeping...', DISABLE)
        time.sleep(120)

    # Set up syslog UDP listener
    try:
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp.bind(('', SYSLOG_UDP_PORT))
    except socket.error, e:
        LOG.error('Syslog UDP error: %s', e)
        sys.exit(2)
    LOG.info('Listening on syslog port 514/udp')

    # Set up syslog TCP listener
    try:
        tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        tcp.bind(('', SYSLOG_TCP_PORT))
        tcp.listen(5)
    except socket.error, e:
        LOG.error('Syslog TCP error: %s', e)
        sys.exit(2)
    LOG.info('Listening on syslog port 514/tcp')

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
        LOG.error('Stomp connection error: %s', e)

    while True:
        try:
            ip, op, rdy = select.select([udp,tcp], [], [])
            for i in ip:
                if i == udp:
                    data = udp.recv(4096)
                    LOG.debug('Syslog UDP: %s', data)
                    send_syslog(data)
                if i == tcp:
                    client,addr = tcp.accept()
                    data = client.recv(4096)
                    client.close()
                    LOG.debug('Syslog TCP: %s', data)
                    send_syslog(data)

            send_heartbeat()
            time.sleep(0.01)
        except (KeyboardInterrupt, SystemExit):
            conn.disconnect()
            os.unlink(PIDFILE)
            sys.exit(0)

if __name__ == '__main__':
    # TODO(nsatterl): read in options like --debug on the command line
    # config.parse_args(sys.argv)
    logging.setup("alert-syslog")

    main()