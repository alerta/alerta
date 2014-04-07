
import sys
import socket
import select
import re

from alerta.common import config
from alerta.common import log as logging
from alerta.common.daemon import Daemon
from alerta.syslog.priority import priority_to_code, decode_priority
from alerta.common.alert import Alert
from alerta.common.heartbeat import Heartbeat
from alerta.common.transform import Transformers
from alerta.common.dedup import DeDup
from alerta.common.api import ApiClient
from alerta.common.graphite import StatsD

__version__ = '3.0.3'

LOG = logging.getLogger(__name__)
CONF = config.CONF


class SyslogDaemon(Daemon):

    syslog_opts = {
        'user_id': 'root',
        'use_syslog': False,
        'syslog_udp_port': 514,
        'syslog_tcp_port': 514,
    }

    def __init__(self, prog, **kwargs):

        config.register_opts(SyslogDaemon.syslog_opts)

        Daemon.__init__(self, prog, kwargs)

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

        self.statsd = StatsD()  # graphite metrics

        self.api = ApiClient()

        self.dedup = DeDup(by_value=True)

        count = 0
        while not self.shuttingdown:
            try:
                LOG.debug('Waiting for syslog messages...')
                ip, op, rdy = select.select([udp, tcp], [], [], CONF.loop_every)
                if ip:
                    for i in ip:
                        if i == udp:
                            data, addr = udp.recvfrom(4096)
                            data = unicode(data, 'utf-8', errors='ignore')
                            LOG.debug('Syslog UDP data received from %s: %s', addr, data)
                        if i == tcp:
                            client, addr = tcp.accept()
                            data = client.recv(4096)
                            data = unicode(data, 'utf-8', errors='ignore')
                            client.close()
                            LOG.debug('Syslog TCP data received from %s: %s', addr, data)

                        syslogAlerts = self.parse_syslog(addr[0], data)
                        for syslogAlert in syslogAlerts:
                            if self.dedup.is_send(syslogAlert):
                                try:
                                    self.api.send(syslogAlert)
                                except Exception, e:
                                    LOG.warning('Failed to send alert: %s', e)
                                self.statsd.metric_send('alert.syslog.alerts.total', 1)

                    count += 1
                if not ip or count % 5 == 0:
                    LOG.debug('Send heartbeat...')
                    heartbeat = Heartbeat(tags=[__version__])
                    try:
                        self.api.send(heartbeat)
                    except Exception, e:
                        LOG.warning('Failed to send heartbeat: %s', e)

            except (KeyboardInterrupt, SystemExit):
                self.shuttingdown = True

        LOG.info('Shutdown request received...')
        self.running = False

    def parse_syslog(self, addr, data):

        LOG.debug('Parsing syslog message...')
        syslogAlerts = list()

        event = None
        resource = None

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
                    LOG.error("Could not parse RFC 5424 syslog message: %s", msg)
                    continue

            elif re.match(r'<(\d{1,3})>\S{3}\s', msg):
                # Parse RFC 3164 compliant message
                m = re.match(r'<(\d{1,3})>\S{3}\s{1,2}\d?\d \d{2}:\d{2}:\d{2} (\S+)( (\S+):)? (.*)', msg)
                if m:
                    PRI = int(m.group(1))
                    HOSTNAME = m.group(2)
                    TAG = m.group(4)
                    MSG = m.group(5)
                    LOG.info("Parsed RFC 3164 message OK")
                else:
                    LOG.error("Could not parse RFC 3164 syslog message: %s", msg)
                    continue

            elif re.match('<\d+>.*%[A-Z0-9_-]+', msg):
                # Parse Cisco Syslog message
                m = re.match('<(\d+)>.*(%([A-Z0-9_-]+)):? (.*)', msg)
                if m:
                    LOG.debug(m.groups())
                    PRI = int(m.group(1))
                    CISCO_SYSLOG = m.group(2)
                    try:
                        CISCO_FACILITY, CISCO_SEVERITY, CISCO_MNEMONIC = m.group(3).split('-')
                    except ValueError, e:
                        LOG.error('Could not parse Cisco syslog - %s: %s', e, m.group(3))
                        CISCO_FACILITY = CISCO_SEVERITY = CISCO_MNEMONIC = 'na'

                    TAG = CISCO_MNEMONIC
                    MSG = m.group(4)

                    event = CISCO_SYSLOG

                    # replace IP address with a hostname, if necessary
                    try:
                        socket.inet_aton(addr)
                        (resource, _, _) = socket.gethostbyaddr(addr)
                    except (socket.error, socket.herror):
                        resource = addr

                    resource = '%s:%s' % (resource, CISCO_FACILITY)
                else:
                    LOG.error("Could not parse Cisco syslog message: %s", msg)
                    continue

            facility, level = decode_priority(PRI)

            # Defaults
            event = event or '%s%s' % (facility.capitalize(), level.capitalize())
            resource = resource or '%s%s' % (HOSTNAME, ':' + TAG if TAG else '')
            severity = priority_to_code(level)
            group = 'Syslog'
            value = level
            text = MSG
            environment = 'PROD'
            service = ['Platform']
            tags = ['%s.%s' % (facility, level)]
            correlate = list()
            timeout = None
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
                raw_data=raw_data,
            )

            suppress = Transformers.normalise_alert(syslogAlert, facility=facility, level=level)
            if suppress:
                LOG.info('Suppressing %s.%s alert', facility, level)
                LOG.debug('%s', syslogAlert)
                continue

            if syslogAlert.get_type() == 'Heartbeat':
                syslogAlert = Heartbeat(origin=syslogAlert.origin, timeout=syslogAlert.timeout)

            syslogAlerts.append(syslogAlert)

        return syslogAlerts
