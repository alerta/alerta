
import os
import sys
import socket
import select
import re
import yaml
import fnmatch

from alerta.common import config
from alerta.common import log as logging
from alerta.common.daemon import Daemon
from alerta.alert import Alert, Heartbeat
from alerta.alert import syslog
from alerta.common.mq import Messaging

Version = '2.0.0'

LOG = logging.getLogger(__name__)
CONF = config.CONF

#TODO(nsatterl): add this to default system config
SYSLOGCONF = '/opt/alerta/alerta/alert-syslog.yaml'
PARSERDIR = '/opt/alerta/bin/parsers'


class SyslogDaemon(Daemon):

    def run(self):

        self.running = True

        LOG.info('Starting UDP listener...')
        # Set up syslog UDP listener
        try:
            udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp.bind(('', CONF.syslog_udp_port))
        except socket.error, e:
            LOG.error('Syslog UDP error: %s', e)
            sys.exit(2)
        LOG.info('Listening on syslog port %s/udp' % CONF.syslog_udp_port)

        LOG.info('Starting TCP listener...')
        # Set up syslog TCP listener
        try:
            tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            tcp.bind(('', CONF.syslog_tcp_port))
            tcp.listen(5)
        except socket.error, e:
            LOG.error('Syslog TCP error: %s', e)
            sys.exit(2)
        LOG.info('Listening on syslog port %s/tcp' % CONF.syslog_tcp_port)

        # Connect to message queue
        self.mq = Messaging()
        self.mq.connect()

        while not self.shuttingdown:
            try:
                LOG.debug('Waiting for syslog messages...')
                ip, op, rdy = select.select([udp, tcp], [], [], CONF.heartbeat_every)
                if ip:
                    for i in ip:
                        if i == udp:
                            data = udp.recv(4096)
                            LOG.debug('Syslog UDP data received: %s', data)
                            syslogAlert = self.parse_syslog(data)
                        if i == tcp:
                            client, addr = tcp.accept()
                            data = client.recv(4096)
                            client.close()
                            LOG.debug('Syslog TCP data received: %s', data)
                            syslogAlert = self.parse_syslog(data)

                        self.mq.send(syslogAlert)
                else:
                    LOG.debug('Send heartbeat...')
                    heartbeat = Heartbeat(version=Version)
                    self.mq.send(heartbeat)

            except (KeyboardInterrupt, SystemExit):
                self.shuttingdown = True

        LOG.info('Shutdown request received...')
        self.running = False

        LOG.info('Disconnecting from message broker...')
        self.mq.disconnect()

    def parse_syslog(self, data):

        LOG.debug('Parsing syslog message...')

        for msg in data.split('\n'):

            if re.match('<\d+>1', msg):
                # Parse RFC 5424 compliant message
                m = re.match(r'<(\d+)>1 (\S+) (\S+) (\S+) (\S+) (\S+) (.*)', msg)
                if m:
                    PRI = int(m.group(1))
                    ISOTIMESTAMP = m.group(2)
                    HOSTNAME = m.group(3)
                    APPNAME = m.group(4)
                    PROCID = m.group(5)
                    MSGID = m.group(6)
                    TAG = '%s[%s] %s' % (APPNAME, PROCID, MSGID)
                    MSG = m.group(7)
                    LOG.info("Parsed RFC 5424 message OK")
                else:
                    LOG.error("Could not parse syslog RFC 5424 message: %s", msg)
                    return

            else:
                # Parse RFC 3164 compliant message
                m = re.match(r'<(\d{1,3})>\S{3}\s{1,2}\d?\d \d{2}:\d{2}:\d{2} (\S+)( (\S+):)? (.*)', msg)
                if m:
                    PRI = int(m.group(1))
                    HOSTNAME = m.group(2)
                    TAG = m.group(4)
                    MSG = m.group(5)
                    LOG.info("Parsed RFC 3164 message OK")
                else:
                    LOG.error("Could not parse syslog RFC 3164 message: %s", msg)
                    return

            facility, level = syslog.decode_priority(PRI)

            # Defaults
            event       = '%s%s' % (facility.capitalize(), level.capitalize())
            resource    = '%s%s' % (HOSTNAME, ':' + TAG if TAG else '')
            severity    = syslog.priority_to_code(level)
            group       = 'Syslog'
            value       = facility
            text        = MSG
            environment = ['INFRA']
            service     = ['Infrastructure']
            tags        = ['%s.%s' % (facility, level)]
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

            syslogAlert = Alert(
                resource=resource,
                event=event,
                correlate=correlate,
                group=group,
                value=value,
                severity=severity,
                environment=environment,
                service=service,
                text=text,
                event_type='syslogAlert',
                tags=tags,
                origin='%s/%s' % ('alert-syslog', os.uname()[1]),
                raw_data=msg,
            )

            return syslogAlert







