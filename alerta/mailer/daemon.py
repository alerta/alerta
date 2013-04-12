
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

Version = '2.0.1'

LOG = logging.getLogger(__name__)
CONF = config.CONF


class MailerMessage(MessageHandler):

    def __init__(self, mq, tokens):

        self.mq = mq
        self.tokens = tokens

        MessageHandler.__init__(self)

    def on_message(self, headers, body):

        LOG.debug("Received: %s", body)

        mailAlert = Alert.parse_alert(body)

        if mailAlert.severity == severity_code.NORMAL and mailAlert.previous_severity == severity_code.UNKNOWN:
            LOG.info('%s: Skip alert because not clearing a known alarm', mailAlert.get_id())
            return

        # Only send email for CRITICAL, MAJOR, MINOR or related alerts
        if ((mailAlert.severity == severity_code.WARNING
                and mailAlert.previous_severity in [severity_code.NORMAL, severity_code.UNKNOWN])
            or (mailAlert.severity == severity_code.NORMAL
                and mailAlert.previous_severity == severity_code.WARNING)):
            LOG.debug('Alert %s not of sufficient severity to warrant an email. Skipping.', mailAlert.get_id())
            return

        if not self.tokens.get_token():
            LOG.warning('%s : No tokens left, rate limiting this alert', headers['correlation-id'])
            return

        email = Mailer(mailAlert)

        mail_to = CONF.mail_list.split(',')
        for tag in mailAlert.tags:
            if tag.startswith('email'):
                mail_to.append(tag.split(':')[1])
        email.send(mail_to=mail_to)

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

