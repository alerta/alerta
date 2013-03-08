
import time
import threading

from alerta.common import config
from alerta.common import log as logging
from alerta.common.daemon import Daemon
from alerta.alert import Alert, Heartbeat, severity
from alerta.common.mq import Messaging, MessageHandler


Version = '2.0.0'

LOG = logging.getLogger(__name__)
CONF = config.CONF

_TokenThread = None            # Worker thread object
_Lock = threading.Lock()       # Synchronization lock
TOKEN_LIMIT = 20
_token_rate = 30               # Add a token every 30 seconds
tokens = 20


class MailerMessage(MessageHandler):

    def on_message(self, headers, body):
        global tokens

        LOG.debug("Received: %s", body)

        mailAlert = Alert.parse_alert(body)
        alert = mailAlert.get_body()

        # Only send email for CRITICAL, MAJOR or related alerts
        if (alert['severity'] not in [severity.CRITICAL, severity.MAJOR]
                or alert['previousSeverity'] not in [severity.CRITICAL, severity.MAJOR]):
            return

        if tokens:
            _Lock.acquire()
            tokens -= 1
            _Lock.release()
            LOG.debug('Taken a token, there are only %d left', tokens)
        else:
            LOG.warning('%s : No tokens left, rate limiting this alert', alert['lastReceiveId'])
            return

        text, html = format_mail(alert)
        subject = '[%s] %s' % (alert['status'], alert['summary'])

        LOG.info('%s : Send email to %s', alert['lastReceiveId'], ','.join(CONF.mail_list))
        send_mail(subject, text, html)




class MailerDaemon(Daemon):

    def run(self):

        self.running = True

        # Start token bucket thread
        _TokenThread = TokenTopUp()
        _TokenThread.start()

        # Connect to message queue
        self.mq = Messaging()
        self.mq.connect(callback=MailerMessage())
        self.mq.subscribe(destination=CONF.outbound_queue)

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

        LOG.info('Disconnecting from message broker...')
        self.mq.disconnect()


class TokenTopUp(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.running = False
        self.shuttingdown = False

    def shutdown(self):
        self.shuttingdown = True
        if not self.running:
            return
        self.join()

    def run(self):
        global _token_rate, tokens
        self.running = True

        while not self.shuttingdown:
            if self.shuttingdown:
                break

            if tokens < TOKEN_LIMIT:
                _Lock.acquire()
                tokens += 1
                _Lock.release()

            if not self.shuttingdown:
                time.sleep(_token_rate)

        self.running = False
