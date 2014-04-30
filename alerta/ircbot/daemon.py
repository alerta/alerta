
import time
import threading

import irc.bot
import irc.client

from alerta.common import config
from alerta.common import log as logging
from alerta.common.daemon import Daemon
from alerta.common.alert import AlertDocument
from alerta.common.heartbeat import Heartbeat
from alerta.common.amqp import Messaging, FanoutConsumer
from alerta.common.api import ApiClient

__version__ = '3.0.4'

LOG = logging.getLogger(__name__)
CONF = config.CONF


class IrcbotServer(threading.Thread, irc.bot.SingleServerIRCBot):

    def __init__(self):

        LOG.info('Connecting to IRC server %s:%s', CONF.irc_host, CONF.irc_port)

        irc.bot.SingleServerIRCBot.__init__(self, [(CONF.irc_host, CONF.irc_port)], CONF.irc_user, CONF.irc_user)
        threading.Thread.__init__(self)

        self.channel = CONF.irc_channel
        self.api = ApiClient()

    def run(self):

        self._connect()
        super(irc.bot.SingleServerIRCBot, self).start()

        LOG.info('Connected to %s:%s', CONF.irc_host, CONF.irc_port)

    def on_welcome(self, connection, event):

        connection.join(self.channel)
        LOG.info('Joined %s', self.channel)

    def on_pubmsg(self, connection, event):

        try:
            cmd, args = event.arguments[0].split(' ', 1)
        except ValueError:
            cmd = event.arguments[0]
            args = None
        self.do_command(event, cmd, args)

    def do_command(self, event, cmd, args):

        if cmd == "disconnect":
            self.disconnect()
        elif cmd == "die":
            self.die()
        elif cmd == "ack" and args:
            self.api.ack_alert(args)
        elif cmd == "delete" and args:
            self.api.delete_alert(args)
        else:
            self.connection.privmsg(self.channel, "huh?")


class IrcbotMessage(FanoutConsumer, threading.Thread):

    def __init__(self, irc):

        self.irc = irc

        mq = Messaging()
        self.connection = mq.connection

        FanoutConsumer.__init__(self, self.connection)
        threading.Thread.__init__(self)

    def on_message(self, body, message):

        LOG.debug("Received: %s", body)
        try:
            ircAlert = AlertDocument.parse_alert(body)
        except ValueError:
            return

        if ircAlert:
            LOG.debug('%s : Send IRC message to %s', ircAlert.get_id(), CONF.irc_channel)
            msg = '%s [%s] %s - %s %s is %s on %s %s' % (
                ircAlert.get_id(short=True), ircAlert.status, ircAlert.environment, ircAlert.severity.capitalize(),
                ircAlert.event, ircAlert.value, ','.join(ircAlert.service), ircAlert.resource)
            try:
                self.irc.connection.privmsg(CONF.irc_channel, msg)
            except irc.client.ServerNotConnectedError, e:
                LOG.error('Could not send message to IRC server %s:%s: %s', CONF.irc_host, CONF.irc_port, e)


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

        ircbot = IrcbotServer()

        mq = IrcbotMessage(ircbot)
        mq.start()

        ircbot.start()

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
            ircbot.should_stop = True
