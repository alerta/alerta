#!/usr/bin/env python
########################################
#
# alert-pager.py - Alert pager to page people with alerts
#
########################################

import os
import sys
import time
import threading
import socket
import select
import re
try:
    import json
except ImportError:
    import simplejson as json
import stomp
import logging

__version__ = '1.0.0'

BROKER_LIST  = [('localhost', 61613)] # list of brokers for failover
NOTIFY_TOPIC = '/topic/notify'

DISABLE = '/opt/alerta/conf/alert-pager.disable'
LOGFILE = '/var/log/alerta/alert-pager.log'
PIDFILE = '/var/run/alerta/alert-pager.pid'

LOGFILE = '/home/shuggins/alert-pager.log'
PIDFILE = '/home/shuggins/alert-pager.pid'


_TokenThread = None            # Worker thread object
_Lock = threading.Lock()       # Synchronization lock
TOKEN_LIMIT = 10
_token_rate = 60                # Add a token every 60 seconds
tokens = 5

def should_we_page(alert):
        logging.debug('Alert keys are %s', ', '.join(alert.keys()))
	regexp = re.compile('AlertSender')
	if alert['severity'] in [ 'NORMAL', 'CRITICAL'] and alert['environment'] in ['INFRA'] and regexp.match(alert['event']) and alert['group'] in ['Alerta'] and alert['service'] in ['Servers']:
		return 1
	return 0


class MessageHandler(object):
    def on_error(self, headers, body):
        logging.error('Received an error %s', body)

    def on_message(self, headers, body):
        global tokens

        logging.debug("Received alert : %s", body)

        alert = dict()
        alert = json.loads(body)

	logging.debug('%s : Checking', alert['lastReceiveId'])

	if not should_we_page(alert):
        	logging.debug('%s : NOT PAGING for [%s] %s', alert['lastReceiveId'], alert['status'], alert['summary'])
		return

	# [CLOSED] infra.servers.monsvr51 NORMAL AlertSender3 is BINGLE!
	pager_message = '[%s] %s %s %s is %s' % (alert['status'], alert['resource'], alert['severity'], alert['event'], alert['value'])

        if tokens:
            _Lock.acquire()
            tokens -= 1
            _Lock.release()
            logging.debug('Taken a token, there are only %d left', tokens)
        else:
            logging.warning('%s : No tokens left, rate limiting this alert: %s', alert['lastReceiveId'], pager_mesage)
            # XXX Do magic XXX
            # Alert on the fact there aren't any tokens left?
            return

        try:
            logging.info('%s : paging with %s', alert['lastReceiveId'], pager_message)
            if alert['status'] == 'CLOSED':
		action = "resolve"
            else:
		action = "trigger"
            incident_key = '%s-%s' % (alert['resource'], alert['event'])
            logging.debug('Would page with %s and %s', incident_key, pager_message)
            
        except Exception, e:
            logging.error('%s : pager sending "%s" failed - %s', alert['lastReceiveId'], pager_message, e)

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
    global conn

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s alert-pager[%(process)d] %(levelname)s - %(message)s", filename=LOGFILE)
    logging.info('Starting up Alert Pager version %s', __version__)

    # Write pid file
    if os.path.isfile(PIDFILE):
        logging.error('%s already exists, exiting', PIDFILE)
	f = open(PIDFILE)
	pid = f.read()
	f.close()
	try:
		os.kill(int(pid), 0)
        	sys.exit(1)
	except OSError:
		pass

    file(PIDFILE, 'w').write(str(os.getpid()))

    while os.path.isfile(DISABLE):
        logging.warning('Disable flag exists (%s). Sleeping...', DISABLE)
        time.sleep(120)

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
            time.sleep(0.5)
        except (KeyboardInterrupt, SystemExit):
            conn.disconnect()
            os.unlink(PIDFILE)
            sys.exit(0)

if __name__ == '__main__':
    main()
