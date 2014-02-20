
import time

from alerta.common import config
from alerta.common import log as logging
from alerta.common.daemon import Daemon
from alerta.common.alert import Alert
from alerta.common.heartbeat import Heartbeat
from alerta.common import severity_code, status_code
from alerta.common.mq import Messaging, MessageHandler
from alerta.pagerduty.pdclientapi import PagerDutyClient

Version = '2.1.1'

LOG = logging.getLogger(__name__)
CONF = config.CONF


class PagerDutyMessage(MessageHandler):

    def __init__(self, mq):

        self.mq = mq

        self.pd = PagerDutyClient()

        MessageHandler.__init__(self)

    def on_message(self, headers, body):

        LOG.debug("Received: %s", body)
        try:
            pdAlert = Alert.parse_alert(body)
        except ValueError:
            return

        if 'pagerduty' not in pdAlert.tags.keys():
            return

        if pdAlert.status == status_code.OPEN:
            self.pd.trigger_event(pdAlert)
        elif pdAlert.status == status_code.ACK:
            self.pd.acknowledge_event(pdAlert)
        elif pdAlert.status == status_code.CLOSED:
            self.pd.resolve_event(pdAlert)

    def on_disconnected(self):

        self.mq.reconnect()


class PagerDutyDaemon(Daemon):

    pagerduty_opts = {
        'pagerduty_subdomain': '',
        'pagerduty_api_key': '',
    }

    def __init__(self, prog, **kwargs):

        config.register_opts(PagerDutyDaemon.pagerduty_opts)

        Daemon.__init__(self, prog, kwargs)

    def run(self):

        self.running = True

        # Connect to message queue
        self.mq = Messaging()
        self.mq.connect(callback=PagerDutyMessage(self.mq))
        self.mq.subscribe(destination=CONF.outbound_topic)   # TODO(nsatterl): use dedicated queue?

        while not self.shuttingdown:
            try:
                LOG.debug('Waiting for PagerDuty messages...')
                time.sleep(CONF.loop_every)

                LOG.debug('Send heartbeat...')
                heartbeat = Heartbeat(version=Version)
                self.mq.send(heartbeat)

            except (KeyboardInterrupt, SystemExit):
                self.shuttingdown = True

        LOG.info('Shutdown request received...')
        self.running = False

        LOG.info('Disconnecting from message broker...')
        self.mq.disconnect()

