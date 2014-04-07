
import time
import threading

from alerta.common import config
from alerta.common import log as logging
from alerta.common.daemon import Daemon
from alerta.common.api import ApiClient
from alerta.common.amqp import Messaging, FanoutConsumer
from alerta.common.alert import AlertDocument
from alerta.common.heartbeat import Heartbeat
from alerta.common import severity_code, status_code
from alerta.pagerduty.pdclientapi import PagerDutyClient

__version__ = '3.0.3'

LOG = logging.getLogger(__name__)
CONF = config.CONF


class PagerDutyMessage(FanoutConsumer, threading.Thread):

    def __init__(self):

        mq = Messaging()

        FanoutConsumer.__init__(self, mq.connection)
        threading.Thread.__init__(self)

        self.pd = PagerDutyClient()

    def on_message(self, body, message):

        LOG.debug("Received: %s", body)
        try:
            pdAlert = AlertDocument.parse_alert(body)
        except ValueError:
            return

        if pdAlert:
            if not any(tag.startswith('pagerduty') for tag in pdAlert.tags):
                return

            # do not trigger new incidents from updates
            if pdAlert.origin == 'pagerduty/webhook':  # set by alerta /pagerduty API endpoint
                return

            for tag in pdAlert.tags:
                if tag.startswith('pagerduty'):
                    _, service = tag.split('=', 1)

            LOG.info('PagerDuty Incident on %s %s -> %s', service, pdAlert.get_id(), pdAlert.status)

            incident_key = pdAlert.get_id()
            if pdAlert.status == status_code.OPEN:
                self.pd.trigger_event(pdAlert, service, incident_key=incident_key)
            elif pdAlert.status == status_code.ACK:
                self.pd.acknowledge_event(pdAlert, service, incident_key=incident_key)
            elif pdAlert.status == status_code.CLOSED:
                self.pd.resolve_event(pdAlert, service, incident_key=incident_key)


class PagerDutyDaemon(Daemon):

    pagerduty_opts = {
        'pagerduty_subdomain': '',
        'pagerduty_api_key': ''
    }

    def __init__(self, prog, **kwargs):

        config.register_opts(PagerDutyDaemon.pagerduty_opts)

        Daemon.__init__(self, prog, kwargs)

    def run(self):

        pd = PagerDutyMessage()
        pd.start()

        self.api = ApiClient()

        try:
            while True:
                LOG.debug('Send heartbeat...')
                heartbeat = Heartbeat(tags=[__version__])
                try:
                    self.api.send(heartbeat)
                except Exception, e:
                    LOG.warning('Failed to send heartbeat: %s', e)
                time.sleep(CONF.loop_every)
        except (KeyboardInterrupt, SystemExit):
            pd.should_stop = True

