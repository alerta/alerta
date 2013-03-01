#!/usr/bin/env python
########################################
#
# alert-ircbot.py - Alert IRC client
#
########################################

import sys
import time
import threading
import socket
import select
import json
import urllib2

from alerta.common import config
from alerta.common import log as logging
from alerta.common.daemon import Daemon
from alerta.alert import Alert, Heartbeat
from alerta.common.mq import Messaging

LOG = logging.getLogger(__name__)
CONF = config.CONF

IRC_SERVER = 'irc.gudev.gnl:6667'
IRC_CHANNEL = '#alerts-dev'
IRC_USER = 'alerta'

API_SERVER = 'monitoring.guprod.gnl'

_SELECT_TIMEOUT = 30

#
# An IRC client may send 1 message every 2 seconds
# See section 5.8 in http://datatracker.ietf.org/doc/rfc2813/
#
_TokenThread = None            # Worker thread object
_Lock = threading.Lock()       # Synchronization lock
TOKEN_LIMIT = 5
_token_rate = 2                # Add a token every 2 seconds
tokens = 5


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


# TODO(nsatterl): this should be in the Alert class
def ack_alert(alertid):

    url = "http://%s/alerta/app/v1/alerts/alert/%s" % (API_SERVER, alertid)
    params = json.dumps({'status': 'ACK'})
    LOG.info('ACK request %s', url)

    try:
        output = urllib2.urlopen(url, params).read()
        response = json.loads(output)['response']
    except urllib2.URLError, e:
        LOG.error('Could not post request and/or parse response from %s - %s', url, e)
        return

    if response['status'] == 'error':
        LOG.error('Message not ACKed - %s', response['message'])
        return

    LOG.info('Successfully ACKed alert %s', alertid)
    return


class MessageHandler(object):
    global tokens

    def __init__(self, irc):
        self.irc = irc

    def on_connecting(self, host_and_port):
        LOG.info('Connecting to %s', host_and_port)

    def on_connected(self, headers, body):
        LOG.info('Connected to %s %s', headers, body)

    def on_disconnected(self):
        # TODO(nsatterl): auto-reconnect
        LOG.error('Connection to messaging server has been lost.')

    def on_message(self, headers, body):

        if tokens:
            _Lock.acquire()
            tokens -= 1
            _Lock.release()
            LOG.debug('Taken a token, there are only %d left', tokens)
        else:
            LOG.warning('%s : No tokens left, rate limiting this alert', 'FIXME')  #TODO(nsatterl): alert['lastReceiveId'])
            return

        LOG.debug("Received alert : %s", body)

        if headers['type'].endswith('Alert'):
            alert = Alert.parse_alert(body)
            if alert:
                LOG.info('%s : Send IRC message to %s', alert['lastReceiveId'], IRC_CHANNEL)
                shortid = alert['id'].split('-')[0]
                try:
                    self.irc.send(
                        'PRIVMSG %s :%s [%s] %s\r\n' % (IRC_CHANNEL, shortid, alert['status'], alert['summary']))
                except Exception, e:
                    LOG.error('%s : IRC send failed - %s', alert['lastReceiveId'], e)

    def on_receipt(self, headers, body):
        LOG.debug('Receipt received %s %s', headers, body)

    def on_error(self, headers, body):
        LOG.error('Send failed %s %s', headers, body)

    def on_send(self, headers, body):
        LOG.debug('Sending message %s %s', headers, body)


class IrcbotDaemon(Daemon):
    def run(self):
        self.running = True

        # Start token bucket thread
        _TokenThread = TokenTopUp()
        _TokenThread.start()

        # Connect to IRC server
        try:
            irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server, port = IRC_SERVER.split(':')
            irc.connect((server, int(port)))
            irc.send('NICK %s\r\n' % IRC_USER)
            irc.send('USER %s 8 * : %s\r\n' % (IRC_USER, IRC_USER))
            LOG.debug('USER -> %s', irc.recv(4096))
            irc.send('JOIN %s\r\n' % IRC_CHANNEL)
            LOG.debug('JOIN ->  %s', irc.recv(4096))
        except Exception, e:
            LOG.error('IRC connection error: %s', e)
            sys.exit(1)

        LOG.info('Joined IRC channel %s on %s as USER %s', IRC_CHANNEL, IRC_SERVER, IRC_USER)

        # Connect to message queue
        self.mq = Messaging()
        self.mq.connect(callback=MessageHandler(irc))
        self.mq.connect()

        while not self.shuttingdown:
            try:
                ip, op, rdy = select.select([irc], [], [], _SELECT_TIMEOUT)
                for i in ip:
                    if i == irc:
                        data = irc.recv(4096)
                        if len(data) > 0:
                            if 'ERROR' in data:
                                LOG.error('IRC server: %s', data)
                            else:
                                LOG.debug('IRC server: %s', data)
                        if 'PING' in data:
                            LOG.info('IRC PING received -> PONG ' + data.split()[1])
                            irc.send('PONG ' + data.split()[1] + '\r\n')
                        if 'ACK' in data:
                            LOG.info('Request to ACK %s by %s', data.split()[4], data.split()[0])
                            ack_alert(data.split()[4])
                        if data.find('!alerta quit') != -1:
                            irc.send('QUIT\r\n')
                if not ip:
                    LOG.debug('Send heartbeat...')
                    heartbeat = Heartbeat()
                    self.mq.send(heartbeat)

                time.sleep(0.1)

            except (KeyboardInterrupt, SystemExit):
                self.shuttingdown = True
                _TokenThread.shutdown()

        LOG.info('Shutdown request received...')
        self.running = False

        LOG.info('Disconnecting from message broker...')
        self.mq.disconnect()