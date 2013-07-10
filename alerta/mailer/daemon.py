
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

Version = '2.0.3'

LOG = logging.getLogger(__name__)
CONF = config.CONF

_EMAIL_HOLD_TIME = 30  # hold emails before sending


class MailerMessage(MessageHandler):

    def __init__(self, mq, onhold, tokens):

        self.mq = mq
        self.onhold = onhold
        self.tokens = tokens

        MessageHandler.__init__(self)

    def on_message(self, headers, body):

        LOG.debug("Received: %s", body)
        try:
            mailAlert = Alert.parse_alert(body)
        except ValueError:
            return

        alertid = mailAlert.get_id()
        severity = mailAlert.get_severity()
        previous_severity = mailAlert.previous_severity

        if severity == severity_code.NORMAL and previous_severity == severity_code.UNKNOWN:
            LOG.info('%s: Skip alert because not clearing a known alarm', alertid)
            return

        # Only send email for CRITICAL, MAJOR, MINOR or related alerts
        if ((severity == severity_code.WARNING
                and previous_severity in [severity_code.NORMAL, severity_code.UNKNOWN])
            or (severity == severity_code.NORMAL
                and previous_severity == severity_code.WARNING)):
            LOG.debug('Alert %s not of sufficient severity to warrant an email. Skipping.', alertid)
            return

        hold_time = time.time() + _EMAIL_HOLD_TIME
        if alertid in self.onhold:
            if severity == severity_code.NORMAL:
                LOG.info('Transient alert %s suppressed', alertid)
                del self.onhold[alertid]
            else:
                self.onhold[alertid] = (mailAlert, hold_time)
        else:
            self.onhold[alertid] = (mailAlert, hold_time)

    def on_disconnected(self):

        self.mq.reconnect()


class MailerDaemon(Daemon):

    def run(self):

        self.running = True

        # Start token bucket thread
        self.tokens = LeakyBucket(tokens=20, rate=30)
        self.tokens.start()

        self.onhold = dict()

        # Connect to message queue
        self.mq = Messaging()
        self.mq.connect(callback=MailerMessage(self.mq, self.onhold, self.tokens))
        self.mq.subscribe(destination=CONF.outbound_topic)

        while not self.shuttingdown:
            try:
                LOG.debug('Send email messages...')
                for alertid in self.onhold.keys():
                    (mailAlert, hold_time) = self.onhold[alertid]

                    if time.time() > hold_time:
                        if not self.tokens.get_token():
                            LOG.warning('%s : No tokens left, rate limiting this alert', alertid)
                            continue

                        email = Mailer(mailAlert)
                        mail_to = CONF.mail_list.split(',')

                        for tag in mailAlert.tags:
                            if tag.startswith('email'):
                                mail_to.append(tag.split(':')[1])
                        email.send(mail_to=mail_to)
                        del self.onhold[alertid]

                time.sleep(CONF.loop_every)

                LOG.debug('Send heartbeat...')
                heartbeat = Heartbeat(version=Version)
                self.mq.send(heartbeat)

            except (KeyboardInterrupt, SystemExit):
                self.shuttingdown = True

        LOG.info('Shutdown request received...')
        self.running = False
        self.tokens.shutdown()

        LOG.info('Disconnecting from message broker...')
        self.mq.disconnect()
