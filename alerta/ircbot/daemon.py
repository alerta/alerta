
import sys
import socket
import select
import json
import urllib2

from alerta.common import config
from alerta.common import log as logging
from alerta.common.daemon import Daemon
from alerta.common.alert import Alert
from alerta.common import status_code
from alerta.common.heartbeat import Heartbeat
from alerta.common.mq import Messaging, MessageHandler
from alerta.common.tokens import LeakyBucket

Version = '2.0.4'

LOG = logging.getLogger(__name__)
CONF = config.CONF


def ack_alert(alertid):

    url = 'http://%s:%s/alerta/api/%s/alerts/alert/%s' % (CONF.api_host, CONF.api_port, CONF.api_version, alertid)
    data = json.dumps({'status': status_code.ACK})
    headers = {'Content-type': 'application/json'}
    LOG.info('ACK request %s', url)

    try:
        request = urllib2.Request(url=url, data=data, headers=headers)
        request.get_method = lambda: 'PUT'
        response = urllib2.urlopen(request)
    except urllib2.URLError, e:
        LOG.error('Request %s failed: %s', url, e)
        return

    else:
        code = response.getcode()
        body = response.read()
        LOG.debug('HTTP response code=%s', code)

    try:
        body = json.loads(body)
    except Exception, e:
        LOG.error('Failed to parse JSON response: %s', body, e)

    if code != 200 or body['response']['status'] == 'error':
        LOG.error('Message not ACKed - %s', body['response']['message'])
        return

    LOG.info('Successfully ACKed alert %s', alertid)
    return


def delete_alert(alertid):

    url = 'http://%s:%s/alerta/api/%s/alerts/alert/%s' % (CONF.api_host, CONF.api_port, CONF.api_version, alertid)
    headers = {'Content-type': 'application/json'}
    LOG.info('DELETE request %s', url)

    try:
        request = urllib2.Request(url=url, headers=headers)
        request.get_method = lambda: 'DELETE'
        response = urllib2.urlopen(request)
    except urllib2.URLError, e:
        LOG.error('Request %s failed: %s', url, e)
        return

    else:
        code = response.getcode()
        body = response.read()
        LOG.debug('HTTP response code=%s', code)

    try:
        body = json.loads(body)
    except Exception, e:
        LOG.error('Failed to parse JSON response: %s', body, e)

    if code != 200 or body['response']['status'] == 'error':
        LOG.error('Message not DELETED - %s', body['response']['message'])
        return

    LOG.info('Successfully DELETED alert %s', alertid)
    return


class IrcbotMessage(MessageHandler):

    def __init__(self, mq, irc, tokens):

        self.mq = mq
        self.irc = irc
        self.tokens = tokens

        MessageHandler.__init__(self)

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
                msg = 'PRIVMSG %s :%s [%s] %s' % (CONF.irc_channel, ircAlert.get_id(short=True),
                                                  ircAlert.status, ircAlert.summary)
                self.irc.send(msg + '\r\n')
            except Exception, e:
                LOG.error('%s : IRC send failed - %s', ircAlert.get_id(), e)

    def on_disconnected(self):

        self.mq.reconnect()


class IrcbotDaemon(Daemon):

    ircbot_opts = {
        'irc_host': 'irc',
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

        # Connect to IRC server
        try:
            irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            irc.connect((CONF.irc_host, CONF.irc_port))
            irc.send('NICK %s\r\n' % CONF.irc_user)
            irc.send('USER %s 8 * : %s\r\n' % (CONF.irc_user, CONF.irc_user))
            LOG.debug('USER -> %s', irc.recv(4096))
            irc.send('JOIN %s\r\n' % CONF.irc_channel)
            LOG.debug('JOIN ->  %s', irc.recv(4096))
        except Exception, e:
            LOG.error('IRC connection error: %s', e)
            sys.exit(1)

        LOG.info('Joined IRC channel %s on %s as USER %s', CONF.irc_channel, CONF.irc_host, CONF.irc_user)

        # Connect to message queue
        self.mq = Messaging()
        self.mq.connect(callback=IrcbotMessage(self.mq, irc, tokens))
        self.mq.subscribe(destination=CONF.outbound_topic)

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
                                ack_alert(data.split()[4])
                            elif 'delete' in data.lower():
                                LOG.info('Request to DELETE %s by %s', data.split()[4], data.split()[0])
                                delete_alert(data.split()[4])
                            elif data.find('!alerta quit') != -1:
                                irc.send('QUIT\r\n')
                            else:
                                LOG.warning('IRC: %s', data)
                        else:
                            i.recv()
                else:
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



