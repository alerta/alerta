
import time
import datetime
import threading

from alerta.common import config
from alerta.common import log as logging
from alerta.common.daemon import Daemon
from alerta.common.api import ApiClient
from alerta.common.amqp import Messaging, FanoutConsumer
from alerta.common.alert import AlertDocument
from alerta.common.heartbeat import Heartbeat
from alerta.common import severity_code, status_code
from alerta.mailer.sendmail import Mailer
from alerta.common.tokens import LeakyBucket

__version__ = '3.0.5'

LOG = logging.getLogger(__name__)
CONF = config.CONF

_EMAIL_HOLD_TIME = 30  # hold emails before sending


class MailerMessage(FanoutConsumer, threading.Thread):

    def __init__(self, onhold, tokens):

        mq = Messaging()
        self.connection = mq.connection

        FanoutConsumer.__init__(self, self.connection)
        threading.Thread.__init__(self)

        self.onhold = onhold
        self.tokens = tokens

    def on_message(self, body, message):

        LOG.debug("Received: %s", body)
        try:
            mailAlert = AlertDocument.parse_alert(body)
        except ValueError:
            return

        alertid = mailAlert.get_id()
        severity = mailAlert.severity
        previous_severity = mailAlert.previous_severity
        status = mailAlert.status

        if status not in [status_code.OPEN, status_code.CLOSED]:
            LOG.info('%s : Do not email alerts with "%s" status', alertid, status)
            return

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
                LOG.info('%s : Extend queue on-hold time to %s', alertid, datetime.datetime.fromtimestamp(hold_time).strftime("%c"))
                self.onhold[alertid] = (mailAlert, hold_time)
        else:
            LOG.info('%s : Queued alert on hold until %s', alertid, datetime.datetime.fromtimestamp(hold_time).strftime("%c"))
            self.onhold[alertid] = (mailAlert, hold_time)


class MailSender(threading.Thread):

    def __init__(self, onhold, tokens):

        threading.Thread.__init__(self)

        self.onhold = onhold
        self.tokens = tokens

    def run(self):

        while True:
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
                    LOG.info('%s : Hold time expired, send alert', alertid)
                    email.send(mail_to=mail_to)
                    try:
                        del self.onhold[alertid]
                    except KeyError:
                        continue

            time.sleep(2)


class MailerDaemon(Daemon):

    def run(self):

        onhold = dict()

        # Start token bucket thread
        tokens = LeakyBucket(tokens=20, rate=30)
        tokens.start()

        mailer = MailerMessage(onhold, tokens)
        mailer.start()

        sender = MailSender(onhold, tokens)
        sender.start()

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
            mailer.should_stop = True
