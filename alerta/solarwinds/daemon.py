
import time
import datetime

from alerta.common import config
from alerta.common import log as logging
from alerta.common.daemon import Daemon
from alerta.common.alert import Alert
from alerta.common.heartbeat import Heartbeat
from alerta.common.dedup import DeDup
from alerta.solarwinds.swis import SwisClient, SOLAR_WINDS_SEVERITY_LEVELS, SOLAR_WINDS_CORRELATED_EVENTS
from alerta.common.mq import Messaging, MessageHandler

Version = '2.0.6'

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

        while True:
            try:
                swis = SwisClient(username=CONF.solarwinds_username, password=CONF.solarwinds_password)
            except Exception, e:
                LOG.error('SolarWinds SWIS Client error: %s', e)
                time.sleep(30)
            else:
                break
        LOG.info('Polling for SolarWinds events on %s' % CONF.solarwinds_host)

        # Connect to message queue
        self.mq = Messaging()
        self.mq.connect(callback=SolarWindsMessage(self.mq))

        self.dedup = DeDup(by_value=True)

        while not self.shuttingdown:
            try:
                LOG.debug('Polling SolarWinds...')
                send_heartbeat = True

                # network, interface and volume events
                try:
                    events = swis.get_npm_events()
                except IOError:
                    events = []
                    send_heartbeat = False

                solarwindsAlerts = self.parse_events(events)
                for solarwindsAlert in solarwindsAlerts:
                    if self.dedup.is_send(solarwindsAlert):
                        self.mq.send(solarwindsAlert)

                # Cisco UCS events
                try:
                    events = swis.get_ucs_events()
                except IOError:
                    events = []
                    send_heartbeat = False

                solarwindsAlerts = self.parse_events(events)
                for solarwindsAlert in solarwindsAlerts:
                    if self.dedup.is_send(solarwindsAlert):
                        self.mq.send(solarwindsAlert)

                if send_heartbeat:
                    LOG.debug('Send heartbeat...')
                    heartbeat = Heartbeat(version=Version)
                    self.mq.send(heartbeat)
                else:
                    LOG.error('SolarWinds failure. Skipping heartbeat.')

                time.sleep(CONF.loop_every)

            except (KeyboardInterrupt, SystemExit):
                self.shuttingdown = True

        LOG.info('Shutdown request received...')
        self.running = False

        LOG.info('Disconnecting from message broker...')
        self.mq.disconnect()

    def parse_events(self, data):

        LOG.debug('Parsing solarwinds event data...')
        LOG.debug(data)

        try:
            data[0]
        except IndexError:
            return []

        try:
            data[0].c0
        except AttributeError:
            data = [data]

        solarwindsAlerts = list()

        for row in data:
            LOG.debug(row)

            event = row.c4.replace(" ", "")
            correlate = SOLAR_WINDS_CORRELATED_EVENTS.get(event, None)
            resource = '%s:%s' % (row.c2, row.c3.lower())
            severity = SOLAR_WINDS_SEVERITY_LEVELS.get(row.c7, None)
            group = 'Orion'
            value = '%s' % row.c6
            text = '%s' % row.c5
            environment = ['INFRA']
            service = ['Network']
            tags = None
            timeout = None
            threshold_info = None
            summary = None
            raw_data = str(row)
            create_time = datetime.datetime.strptime(row.c1[:-5]+'Z', '%Y-%m-%dT%H:%M:%S.%fZ')

            solarwindsAlert = Alert(
                resource=resource,
                event=event,
                correlate=correlate,
                group=group,
                value=value,
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

            suppress = solarwindsAlert.transform_alert()
            if suppress:
                LOG.warning('Suppressing %s alert', solarwindsAlert.event)
                LOG.debug('%s', solarwindsAlert)
                continue

            if solarwindsAlert.get_type() == 'Heartbeat':
                solarwindsAlert = Heartbeat(origin=solarwindsAlert.origin, version='n/a', timeout=solarwindsAlert.timeout)

            solarwindsAlerts.append(solarwindsAlert)

        return solarwindsAlerts
