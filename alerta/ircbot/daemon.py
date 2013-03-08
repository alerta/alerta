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
from alerta.alert import Alert, Heartbeat, status
from alerta.common.mq import Messaging, MessageHandler

Version = '2.0.0'

LOG = logging.getLogger(__name__)
CONF = config.CONF

#
# An IRC client may send 1 message every 2 seconds
# See section 5.8 in http://datatracker.ietf.org/doc/rfc2813/
#

_TokenThread = None            # Worker thread object
_Lock = threading.Lock()       # Synchronization lock
TOKEN_LIMIT = 5
_token_rate = 2                # Add a token every 2 seconds
tokens = 5


# TODO(nsatterl): this should be in the Alert class
def ack_alert(alertid):

    url = "http://%s:%s/%s/alerts/alert/%s" % (CONF.api_host, CONF.api_port, CONF.api_endpoint, alertid)
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


class IrcbotMessage(MessageHandler):

    def __init__(self, irc):

        #super(MessageHandler, self).__init__()

        self.irc = irc

    def on_message(self, headers, body):
        global tokens

        if tokens:
            _Lock.acquire()
            tokens -= 1
            _Lock.release()
            LOG.debug('Taken a token, there are only %d left', tokens)
        else:
            LOG.warning('%s : No tokens left, rate limiting this alert', headers['correlation-id'])
            return

        LOG.debug("Received: %s", body)

        if headers['type'].endswith('Alert'):
            ircAlert = Alert.parse_alert(body)
            if ircAlert:
                LOG.info('%s : Send IRC message to %s', ircAlert.get_id(), CONF.irc_channel)
                try:
                    msg = 'PRIVMSG %s :%s [%s] %s' % (CONF.irc_channel, ircAlert.get_id(short=True),
                                                      ircAlert.alert.get('status', status.UNKNOWN), ircAlert.summary)
                    self.irc.send(msg + '\r\n')
                except Exception, e:
                    LOG.error('%s : IRC send failed - %s', ircAlert.get_id(), e)


class IrcbotDaemon(Daemon):

    def run(self):
        self.running = True

        # Start token bucket thread
        _TokenThread = TokenTopUp()
        _TokenThread.start()

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
        self.mq.connect(callback=IrcbotMessage(irc))
        self.mq.subscribe(destination=CONF.outbound_queue)

        while not self.shuttingdown:
            try:
                LOG.debug('Waiting for IRC messages...')
                ip, op, rdy = select.select([irc], [], [], CONF.loop_every)
                if ip:
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
                else:
                    LOG.debug('Send heartbeat...')
                    heartbeat = Heartbeat(version=Version)
                    self.mq.send(heartbeat)

            except (KeyboardInterrupt, SystemExit):
                self.shuttingdown = True
                _TokenThread.shutdown()

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
