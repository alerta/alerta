
import sys
import socket
import select
import time

from alerta.common import config
from alerta.common import log as logging
from alerta.common.daemon import Daemon
from alerta.common.alert import Alert
from alerta.common.heartbeat import Heartbeat
from alerta.common.amqp import Messaging, FanoutConsumer
from alerta.common.tokens import LeakyBucket
from alerta.common.api import ApiClient

Version = '3.0.0'

LOG = logging.getLogger(__name__)
CONF = config.CONF


class IrcbotMessage(FanoutConsumer):

    def __init__(self, mq, irc, tokens):

        self.irc = irc
        self.tokens = tokens

        FanoutConsumer.__init__(self, mq)

    def on_message(self, headers, body):

        if not self.tokens.get_token():
            LOG.warning('%s : No tokens left, rate limiting this alert', headers['correlation-id'])
            return

        LOG.debug("Received: %s", body)
        try:
            ircAlert = Alert.parse_alert(body)
        except ValueError:
            return

        if ircAlert:
            LOG.info('%s : Send IRC message to %s', ircAlert.get_id(), CONF.irc_channel)
            try:
                msg = 'PRIVMSG %s :%s [%s] %s - %s %s is %s on %s %s' % (CONF.irc_channel, ircAlert.get_id(short=True),
                      ircAlert.status, ircAlert.environment, ircAlert.severity, ircAlert.event, ircAlert.value,
                      ','.join(ircAlert.service), ircAlert.resource)
                self.irc.send(msg + '\r\n')
            except Exception, e:
                LOG.error('%s : IRC send failed - %s', ircAlert.get_id(), e)


class IrcbotDaemon(Daemon):

    ircbot_opts = {
        'irc_host': 'localhost',
        'irc_port': 6667,
        'irc_channel': '#alerts',
        'irc_user': 'alerta',
    }

    def __init__(self, prog, **kwargs):

        config.register_opts(IrcbotDaemon.ircbot_opts)

        Daemon.__init__(self, prog, kwargs)

    def run(self):

        self.running = True

        # An IRC client may send 1 message every 2 seconds
        # See section 5.8 in http://datatracker.ietf.org/doc/rfc2813/
        tokens = LeakyBucket(tokens=20, rate=2)
        tokens.start()

        api = ApiClient()

        # Connect to IRC server
        try:
            irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            irc.connect((CONF.irc_host, CONF.irc_port))
            time.sleep(1)
            irc.send('NICK %s\r\n' % CONF.irc_user)
            time.sleep(1)
            irc.send('USER %s 8 * : %s\r\n' % (CONF.irc_user, CONF.irc_user))
            LOG.debug('USER -> %s', irc.recv(4096))
            time.sleep(1)
            irc.send('JOIN %s\r\n' % CONF.irc_channel)
            LOG.debug('JOIN ->  %s', irc.recv(4096))
        except Exception, e:
            LOG.error('IRC connection error: %s', e)
            sys.exit(1)

        LOG.info('Joined IRC channel %s on %s as USER %s', CONF.irc_channel, CONF.irc_host, CONF.irc_user)

        # Connect to message queue
        mq = Messaging()

        ircbot = IrcbotMessage(mq.connection)
        ircbot.run()

        while not self.shuttingdown:
            try:
                LOG.debug('Waiting for IRC messages...')
                ip, op, rdy = select.select([irc], [], [], CONF.loop_every)
                if ip:
                    for i in ip:
                        if i == irc:
                            data = irc.recv(4096).rstrip('\r\n')
                            if len(data) > 0:
                                if 'ERROR' in data:
                                    LOG.error('%s. Exiting...', data)
                                    sys.exit(1)
                                else:
                                    LOG.debug('%s', data)
                            else:
                                LOG.warning('IRC server sent no data')
                            if 'PING' in data:
                                LOG.info('IRC PING received -> PONG ' + data.split()[1])
                                irc.send('PONG ' + data.split()[1] + '\r\n')
                            elif 'ack' in data.lower():
                                LOG.info('Request to ACK %s by %s', data.split()[4], data.split()[0])
                                api.ack(data.split()[4])
                            elif 'delete' in data.lower():
                                LOG.info('Request to DELETE %s by %s', data.split()[4], data.split()[0])
                                api.delete(data.split()[4])
                            elif data.find('!alerta quit') != -1:
                                irc.send('QUIT\r\n')
                            else:
                                LOG.debug('IRC: %s', data)
                        else:
                            i.recv()
                else:
                    LOG.debug('Send heartbeat...')
                    heartbeat = Heartbeat(tags=[Version])
                    mq.send(heartbeat)

            except (KeyboardInterrupt, SystemExit):
                self.shuttingdown = True

        LOG.info('Shutdown request received...')
        self.running = False
        tokens.shutdown()

        LOG.info('Disconnecting from message broker...')
        mq.disconnect()
