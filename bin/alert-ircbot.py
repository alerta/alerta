#!/usr/bin/env python
########################################
#
# alert-ircbot.py - Alert IRC client
#
########################################

import os
import sys
import time
import threading
import socket
import select
try:
    import json
except ImportError:
    import simplejson as json
import stomp
import logging

__version__ = '1.0'

BROKER_LIST  = [('devmonsvr01',61613), ('localhost', 61613)] # list of brokers for failover
NOTIFY_TOPIC = '/topic/notify'
IRC_SERVER   = 'irc.gudev.gnl:6667'
IRC_CHANNEL  = '#alerts'
IRC_USER     = 'alerta'

LOGFILE = '/var/log/alerta/alert-ircbot.log'
PIDFILE = '/var/run/alerta/alert-ircbot.pid'

#
# An IRC client may send 1 message every 2 seconds
# See section 5.8 in http://datatracker.ietf.org/doc/rfc2813/
#
_TokenThread = None            # Worker thread object
_Lock = threading.Lock()       # Synchronization lock
TOKEN_LIMIT = 5
_token_rate = 2                # Add a token every 2 seconds
tokens = 5

class MessageHandler(object):
    def on_error(self, headers, body):
        logging.error('Received an error %s', body)

    def on_message(self, headers, body):
        global tokens

        logging.debug("Received alert; %s", body)

        alert = dict()
        alert = json.loads(body)

        if tokens:
            _Lock.acquire()
            tokens -= 1
            _Lock.release()
            logging.info('%s : %d tokens left.', alert['lastReceiveId'], tokens)
        else:
            logging.info('%s : Rate limiting this alert because no tokens left (%s)', alert['lastReceiveId'], alert['summary'])
            return

        try:
            logging.info('%s : IRC message %s', alert['lastReceiveId'], alert['summary'])
            irc.send('PRIVMSG '+IRC_CHANNEL+' :'+alert['summary']+'\r\n')
        except Exception, e:
            logging.error('%s : IRC send failed %s %s', alert['lastReceiveId'], e, alert['summary'])

    def on_disconnected(self):
        global conn

        logging.warning('Connection lost. Attempting auto-reconnect to %s', NOTIFY_TOPIC)
        conn.start()
        conn.connect(wait=True)
        conn.subscribe(destination=NOTIFY_TOPIC, ack='auto', headers={'selector': "repeat = 'false'"})

class TokenTopUp(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.running      = False
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

def main():
    global irc, conn

    logging.basicConfig(level=logging.INFO, format="%(asctime)s alert-ircbot[%(process)d] %(levelname)s - %(message)s", filename=LOGFILE)
    logging.info('Starting up Alert IRCbot version %s', __version__)

    # Write pid file
    if os.path.isfile(PIDFILE):
        logging.error('%s already exists, exiting' % PIDFILE)
        sys.exit(1)
    else:
        file(PIDFILE, 'w').write(str(os.getpid()))

    # Connect to IRC server
    try:
        irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server, port = IRC_SERVER.split(':')
        irc.connect((server, int(port)))
        irc.send('NICK %s\r\n' % IRC_USER)
        irc.send('USER %s 8 * : %s\r\n' % (IRC_USER, IRC_USER))
        logging.debug('USER -> %s', irc.recv(4096))
        irc.send('JOIN %s\r\n' % IRC_CHANNEL)
        logging.debug('JOIN ->  %s', irc.recv(4096))
    except Exception, e:
        logging.error('IRC connection error: %s', e)
        sys.exit(2)

    logging.info('Joined IRC channel %s on %s as USER %s', IRC_CHANNEL, IRC_SERVER, IRC_USER)

    # Connect to message broker
    try:
        conn = stomp.Connection(BROKER_LIST)
        conn.set_listener('', MessageHandler())
        conn.start()
        conn.connect(wait=True)
        conn.subscribe(destination=NOTIFY_TOPIC, ack='auto', headers={'selector': "repeat = 'false'"})
    except Exception, e:
        logging.error('Stomp connection error: %s', e)

    # Start token bucket thread
    _TokenThread = TokenTopUp()
    _TokenThread.start()

    while True:
        try:
            ip, op, rdy = select.select([irc], [], [])
            for i in ip:
                if i == irc:
                    data = irc.recv(4096)
                    if data.find('PING') != -1:
                        logging.info('IRC PING received -> PONG '+data.split()[1])
                        irc.send('PONG '+data.split()[1]+'\r\n')
                    if data.find('!alerta quit') != -1:
                        irc.send('QUIT\r\n')

            time.sleep(0.01)
        except (KeyboardInterrupt, SystemExit):
            conn.disconnect()
            _TokenThread.shutdown()
            os.unlink(PIDFILE)
            sys.exit(0)

if __name__ == '__main__':
    main()
