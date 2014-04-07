
import time
import datetime

from alerta.common import config
from alerta.common import log as logging
from alerta.common.daemon import Daemon
from alerta.common.alert import Alert
from alerta.common.heartbeat import Heartbeat
from alerta.common.transform import Transformers
from alerta.common.dedup import DeDup
from alerta.solarwinds.swis import SwisClient, SOLAR_WINDS_SEVERITY_LEVELS, SOLAR_WINDS_CORRELATED_EVENTS
from alerta.common.api import ApiClient

__version__ = '3.0.3'

LOG = logging.getLogger(__name__)
CONF = config.CONF


class SolarWindsDaemon(Daemon):

    solarwinds_opts = {
        'solarwinds_host': 'localhost',
        'solarwinds_username': 'admin',
        'solarwinds_password': '',
        'solarwinds_group': 'websys',
    }

    def __init__(self, prog, **kwargs):

        config.register_opts(SolarWindsDaemon.solarwinds_opts)

        Daemon.__init__(self, prog, kwargs)

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
        self.api = ApiClient()

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
                        self.api.send(solarwindsAlert)

                # Cisco UCS events
                try:
                    events = swis.get_ucs_events()
                except IOError:
                    events = []
                    send_heartbeat = False

                solarwindsAlerts = self.parse_events(events)
                for solarwindsAlert in solarwindsAlerts:
                    if self.dedup.is_send(solarwindsAlert):
                        try:
                            self.api.send(solarwindsAlert)
                        except Exception, e:
                            LOG.warning('Failed to send alert: %s', e)

                if send_heartbeat:
                    LOG.debug('Send heartbeat...')
                    heartbeat = Heartbeat(tags=[__version__])
                    try:
                        self.api.send(heartbeat)
                    except Exception, e:
                        LOG.warning('Failed to send heartbeat: %s', e)
                else:
                    LOG.error('SolarWinds failure. Skipping heartbeat.')

                time.sleep(CONF.loop_every)

            except (KeyboardInterrupt, SystemExit):
                self.shuttingdown = True

        LOG.info('Shutdown request received...')
        self.running = False

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
            environment = 'PROD'
            service = ['Network']
            tags = None
            timeout = None
            raw_data = repr(row)
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
                timeout=timeout,
                create_time=create_time,
                raw_data=raw_data,
            )

            suppress = Transformers.normalise_alert(solarwindsAlert)
            if suppress:
                LOG.info('Suppressing %s alert', solarwindsAlert.event)
                LOG.debug('%s', solarwindsAlert)
                continue

            if solarwindsAlert.get_type() == 'Heartbeat':
                solarwindsAlert = Heartbeat(origin=solarwindsAlert.origin, version='n/a', timeout=solarwindsAlert.timeout)

            solarwindsAlerts.append(solarwindsAlert)

        return solarwindsAlerts
