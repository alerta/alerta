
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

Version = '2.1.0'

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

        if severity in [severity_code.CRITICAL, severity_code.MAJOR]:
            LOG.info('%s : Queue email because alert severity is important', alertid)
        elif previous_severity in [severity_code.CRITICAL, severity_code.MAJOR]:
            LOG.info('%s : Queue email because alert severity was important', alertid)
        else:
            LOG.info('%s : Do not queue email, not important enough', alertid)
            return

        hold_time = time.time() + _EMAIL_HOLD_TIME
        if alertid in self.onhold:
            if severity == severity_code.NORMAL:
                LOG.info('%s : De-queue alert because it has been cleared', alertid)
                del self.onhold[alertid]
            else:
                LOG.info('%s : Extend queue on-hold time to %s', alertid, hold_time)
                self.onhold[alertid] = (mailAlert, hold_time)
        else:
            LOG.info('%s : Queued alert on hold until %s', alertid, hold_time)
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
                    try:
                        (mailAlert, hold_time) = self.onhold[alertid]
                    except KeyError:
                        continue

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
                        try:
                            del self.onhold[alertid]
                        except KeyError:
                            continue

                time.sleep(CONF.loop_every)

                LOG.debug('Send heartbeat...')
                heartbeat = Heartbeat(tags=[Version])
                self.api.send(heartbeat)

            except (KeyboardInterrupt, SystemExit):
                self.shuttingdown = True

        LOG.info('Shutdown request received...')
        self.running = False
        self.tokens.shutdown()

        LOG.info('Disconnecting from message broker...')
        self.mq.disconnect()
