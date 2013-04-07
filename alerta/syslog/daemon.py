
import sys
import socket
import select
import re

from alerta.common import config
from alerta.common import log as logging
from alerta.common.daemon import Daemon
from alerta.alert import Alert, Heartbeat
from alerta.common.dedup import DeDup
from alerta.alert import syslog
from alerta.common.mq import Messaging, MessageHandler

Version = '2.0.2'

LOG = logging.getLogger(__name__)
CONF = config.CONF


class SyslogMessage(MessageHandler):

    def __init__(self, mq):
        self.mq = mq
        MessageHandler.__init__(self)

    def on_disconnected(self):
        self.mq.reconnect()


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
        self.mq.connect(callback=SyslogMessage(self.mq))

        self.dedup = DeDup(by_value=True)

        count = 0
        while not self.shuttingdown:
            try:
                LOG.debug('Waiting for syslog messages...')
                ip, op, rdy = select.select([udp, tcp], [], [], CONF.loop_every)
                if ip:
                    for i in ip:
                        if i == udp:
                            data = udp.recv(4096)
                            LOG.debug('Syslog UDP data received: %s', data)
                        if i == tcp:
                            client, addr = tcp.accept()
                            data = client.recv(4096)
                            client.close()
                            LOG.debug('Syslog TCP data received: %s', data)

                        syslogAlerts = self.parse_syslog(data)
                        for syslogAlert in syslogAlerts:
                            if self.dedup.is_send(syslogAlert):
                                self.mq.send(syslogAlert)
                    count += 1
                if not ip or count % 5 == 0:
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
        syslogAlerts = list()

        for msg in data.split('\n'):

            # NOTE: if syslog msgs aren't being split on newlines and #012 appears instead then
            #       try adding "$EscapeControlCharactersOnReceive off" to rsyslog.conf

            if not msg or 'last message repeated' in msg:
                continue

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
                    continue

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
                    continue

            facility, level = syslog.decode_priority(PRI)

            # Defaults
            event = '%s%s' % (facility.capitalize(), level.capitalize())
            resource = '%s%s' % (HOSTNAME, ':' + TAG if TAG else '')
            severity = syslog.priority_to_code(level)
            group = 'Syslog'
            value = level
            text = MSG
            environment = ['INFRA']
            service = ['Platform']
            tags = ['%s.%s' % (facility, level)]
            correlate = list()
            timeout = None
            threshold_info = None
            summary = None
            raw_data = msg

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
                timeout=timeout,
                threshold_info=threshold_info,
                summary=summary,
                raw_data=raw_data,
            )

            suppress = syslogAlert.transform_alert(facility=facility, level=level)
            if suppress:
                LOG.warning('Suppressing %s.%s alert', facility, level)
                LOG.debug('%s', syslogAlert)
                continue

            syslogAlerts.append(syslogAlert)

        return syslogAlerts







