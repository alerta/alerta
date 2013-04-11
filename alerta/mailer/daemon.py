
import time

from alerta.common import config
from alerta.common import log as logging
from alerta.common.daemon import Daemon
from alerta.common.alert import Alert
from alerta.common.heartbeat import Heartbeat
from alerta.common import severity_code
from alerta.common.mq import Messaging, MessageHandler
from alerta.common.mail import Mailer
from alerta.common.tokens import LeakyBucket

Version = '2.0.0'

LOG = logging.getLogger(__name__)
CONF = config.CONF


class MailerMessage(MessageHandler):

    def __init__(self, mq, tokens):

        self.mq = mq
        self.tokens = tokens

        MessageHandler.__init__(self)

    def on_message(self, headers, body):

        if not self.tokens.get_token():
            LOG.warning('%s : No tokens left, rate limiting this alert', headers['correlation-id'])
            return

        LOG.debug("Received: %s", body)

        mailAlert = Alert.parse_alert(body)
        current_severity, previous_severity = mailAlert.get_severity()

        # Only send email for CRITICAL, MAJOR or related alerts
        if (current_severity not in [severity_code.CRITICAL, severity_code.MAJOR]
                or previous_severity not in [severity_code.CRITICAL, severity_code.MAJOR]):
            return

        email = Mailer(mailAlert)
        email.send()

    def on_disconnected(self):

        self.mq.reconnect()


class MailerDaemon(Daemon):

    def run(self):

        self.running = True

        # Start token bucket thread
        tokens = LeakyBucket(tokens=20, rate=30)
        tokens.start()

        # Connect to message queue
        self.mq = Messaging()
        self.mq.connect(callback=MailerMessage(self.mq, tokens))
        self.mq.subscribe(destination=CONF.outbound_topic)

        while not self.shuttingdown:
            try:
                LOG.debug('Waiting for email messages...')
                time.sleep(CONF.loop_every)

                LOG.debug('Send heartbeat...')
                heartbeat = Heartbeat(version=Version)
                self.mq.send(heartbeat)

            except (KeyboardInterrupt, SystemExit):
                self.shuttingdown = True

        LOG.info('Shutdown request received...')
        self.running = False
        tokens.shutdown()

        LOG.info('Disconnecting from message broker...')
        self.mq.disconnect()

