
import time

from alerta.common import config
from alerta.common import log as logging
from alerta.common.daemon import Daemon
from alerta.common.alert import Alert
from alerta.common.heartbeat import Heartbeat
from alerta.common import severity_code, status_code
from alerta.common.amqp import Messaging, FanoutConsumer
from alerta.common.api import ApiClient
from alerta.pagerduty.pdclientapi import PagerDutyClient

Version = '3.0.0'

LOG = logging.getLogger(__name__)
CONF = config.CONF


class PagerDutyMessage(FanoutConsumer):

    def __init__(self):

        self.pd = PagerDutyClient()

        FanoutConsumer.__init__(self)

    def on_message(self, headers, body):

        LOG.debug("Received: %s", body)
        try:
            pdAlert = Alert.parse_alert(body)
        except ValueError:
            return

        # do not trigger new incidents from updates
        if pdAlert.origin == 'pagerduty/webhook':
            return

        if 'pagerduty' not in pdAlert.tags.keys():
            return

        LOG.info('PagerDuty Incident %s status %s', pdAlert.get_id(), pdAlert.status)

        incident_key = pdAlert.get_id()
        if pdAlert.status == status_code.OPEN:
            self.pd.trigger_event(pdAlert, incident_key=incident_key)
        elif pdAlert.status == status_code.ACK:
            self.pd.acknowledge_event(pdAlert, incident_key=incident_key)
        elif pdAlert.status == status_code.CLOSED:
            self.pd.resolve_event(pdAlert, incident_key=incident_key)


class PagerDutyDaemon(Daemon):

    pagerduty_opts = {
        'pagerduty_subdomain': '',
        'pagerduty_api_key': ''
    }

    def __init__(self, prog, **kwargs):

        config.register_opts(PagerDutyDaemon.pagerduty_opts)

        Daemon.__init__(self, prog, kwargs)

    def run(self):

        self.running = True

        api = ApiClient()

        while not self.shuttingdown:
            try:
                LOG.debug('Waiting for PagerDuty messages...')
                time.sleep(CONF.loop_every)

                LOG.debug('Send heartbeat...')
                heartbeat = Heartbeat(tags=[Version])
                api.send(heartbeat)

            except (KeyboardInterrupt, SystemExit):
                self.shuttingdown = True

        LOG.info('Shutdown request received...')
        self.running = False
