#!/usr/bin/env python
########################################
#
# alert-logger.py - Alert Logger module
#
########################################

import os
import sys
import time
try:
    import json
except ImportError:
    import simplejson as json
import stomp
import datetime
import logging
import urllib2

__version__ = '1.0'

BROKER_LIST  = [('devmonsvr01',61613), ('localhost', 61613)] # list of brokers for failover
LOGGER_QUEUE = '/queue/logger' # XXX note use of queue not topic because all alerts should be logged

LOGFILE = '/var/log/alerta/alert-logger.log'
PIDFILE = '/var/run/alerta/alert-logger.pid'

ES_SERVER   = 'devmonsvr01'
ES_BASE_URL = 'http://%s:9200/logstash' % (ES_SERVER)

class MessageHandler(object):
    def on_error(self, headers, body):
        logging.error('Received an error %s', body)

    def on_message(self, headers, body):
        logging.debug("Received alert : %s", body)

        alert = dict()
        alert = json.loads(body)
        if not alert['tags']:           # Kibana GUI borks if tags are null
            alert['tags'] = 'none'

        logging.info('%s : %s', alert['lastReceiveId'], alert['summary'])

        # Index alerts in ElasticSearch using Logstash format so that logstash GUI and/or Kibana can be used as frontends
        logstash = dict() 
        logstash['@message']     = alert['summary']
        logstash['@source']      = alert['resource']
        logstash['@source_host'] = 'not_used'
        logstash['@source_path'] = alert['origin']
        logstash['@tags']        = alert['tags']
        logstash['@timestamp']   = alert['lastReceiveTime']
        logstash['@type']        = alert['type']
        logstash['@fields']      = alert

        try:
            url = "%s/%s" % (ES_BASE_URL, alert['type'])
            response = urllib2.urlopen(url, json.dumps(logstash)).read()
        except Exception, e:
            logging.error('%s : Alert indexing to %s failed - %s', alert['lastReceiveId'], url, e)
            return

        id = json.loads(response)['_id']
        logging.info('%s : Alert indexed at %s/%s/%s', alert['lastReceiveId'], ES_BASE_URL, alert['type'], id)
        
    def on_disconnected(self):
        global conn

        logging.warning('Connection lost. Attempting auto-reconnect to %s', LOGGER_QUEUE)
        conn.start()
        conn.connect(wait=True)
        conn.subscribe(destination=LOGGER_QUEUE, ack='auto')

def main():
    global conn

    logging.basicConfig(level=logging.INFO, format="%(asctime)s alert-logger[%(process)d] %(levelname)s - %(message)s", filename=LOGFILE)
    logging.info('Starting up Alert Logger version %s', __version__)

    # Write pid file
    if os.path.isfile(PIDFILE):
        logging.error('%s already exists, exiting' % PIDFILE)
        sys.exit(1)
    else:
        file(PIDFILE, 'w').write(str(os.getpid()))

    # Connect to message broker
    try:
        conn = stomp.Connection(BROKER_LIST)
        conn.set_listener('', MessageHandler())
        conn.start()
        conn.connect(wait=True)
        conn.subscribe(destination=LOGGER_QUEUE, ack='auto')
    except Exception, e:
        logging.error('Stomp connection error: %s', e)

    while True:
        try:
            time.sleep(0.01)
        except (KeyboardInterrupt, SystemExit):
            conn.disconnect()
            os.unlink(PIDFILE)
            sys.exit(0)

if __name__ == '__main__':
    main()
