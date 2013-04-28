
import sys
import time
import datetime

from alerta.common import config
from alerta.common import log as logging
from alerta.common.daemon import Daemon
from alerta.common.alert import Alert
from alerta.common.heartbeat import Heartbeat
from alerta.common.dedup import DeDup
from alerta.solarwinds.swis import SwisClient, SOLAR_WINDS_SEVERITY_LEVELS
from alerta.common.mq import Messaging, MessageHandler

Version = '2.0.0'

LOG = logging.getLogger(__name__)
CONF = config.CONF


class SolarWindsMessage(MessageHandler):

    def __init__(self, mq):
        self.mq = mq
        MessageHandler.__init__(self)

    def on_disconnected(self):
        self.mq.reconnect()


class SolarWindsDaemon(Daemon):

    def run(self):

        self.running = True

        LOG.info('Starting SolarWinds poller %s %s...', CONF.solarwinds_username, CONF.solarwinds_password)
        try:
            swis = SwisClient(username=CONF.solarwinds_username, password=CONF.solarwinds_password)
        except Exception, e:
            LOG.error('SolarWinds SWIS Client error: %s', e)
            sys.exit(2)
        LOG.info('Polling for SolarWinds events on %s' % CONF.solarwinds_host)

        # Connect to message queue
        self.mq = Messaging()
        self.mq.connect(callback=SolarWindsMessage(self.mq))

        self.dedup = DeDup(by_value=True)

        while not self.shuttingdown:
            try:
                LOG.debug('Polling SolarWinds...')

                events = swis.get_nw_events()
                solarwindsAlerts = self.parse_events(events)
                for solarwindsAlert in solarwindsAlerts:
                    if self.dedup.is_send(solarwindsAlert):
                        self.mq.send(solarwindsAlert)

                events = swis.get_if_events()
                solarwindsAlerts = self.parse_events(events)
                for solarwindsAlert in solarwindsAlerts:
                    if self.dedup.is_send(solarwindsAlert):
                        self.mq.send(solarwindsAlert)

                events = swis.get_vol_events()
                solarwindsAlerts = self.parse_events(events)
                for solarwindsAlert in solarwindsAlerts:
                    if self.dedup.is_send(solarwindsAlert):
                        self.mq.send(solarwindsAlert)

                LOG.debug('Send heartbeat...')
                heartbeat = Heartbeat(version=Version)
                self.mq.send(heartbeat)

                time.sleep(CONF.loop_every)

            except (KeyboardInterrupt, SystemExit):
                self.shuttingdown = True

        LOG.info('Shutdown request received...')
        self.running = False

        LOG.info('Disconnecting from message broker...')
        self.mq.disconnect()

    def parse_events(self, data):

        LOG.debug('Parsing solarwinds events...')
        solarwindsAlerts = list()

        for d in data:
            LOG.debug(d)
            LOG.debug(SOLAR_WINDS_SEVERITY_LEVELS[d.c7])

            event = d.c4
            resource = '%s:%s' % (d.c2, d.c3)
            severity = SOLAR_WINDS_SEVERITY_LEVELS[d.c7]
            status = 'ack' if d.c6 == 'True' else 'open'
            group = 'Orion'
            value = ''
            text = d.c5
            environment = ['INFRA']
            service = ['Network']
            tags = None
            correlate = list()
            timeout = None
            threshold_info = None
            summary = None
            raw_data = str(d)
            create_time = datetime.datetime.strptime(d.c1[:-5]+'Z', '%Y-%m-%dT%H:%M:%S.%fZ')

            syslogAlert = Alert(
                resource=resource,
                event=event,
                correlate=correlate,
                group=group,
                value=value,
                status=status,
                severity=severity,
                environment=environment,
                service=service,
                text=text,
                event_type='solarwindsAlert',
                tags=tags,
                threshold_info=threshold_info,
                summary=summary,
                timeout=timeout,
                create_time=create_time,
                raw_data=raw_data,
            )

            # suppress = syslogAlert.transform_alert(facility=facility, level=level)
            # if suppress:
            #     LOG.warning('Suppressing %s.%s alert', facility, level)
            #     LOG.debug('%s', syslogAlert)
            #     continue

            solarwindsAlerts.append(syslogAlert)

        return solarwindsAlerts







