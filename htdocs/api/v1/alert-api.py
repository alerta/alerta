#!/usr/bin/env python
########################################
#
# alerta-api.py - Alerter New Alert API
#
########################################

import os, sys
import time
import re
try:
    import json
except ImportError:
    import simplejson as json

import datetime
# STOMP bindings from https://github.com/mozes/stompest
from stompest.simple import Stomp
import logging
import uuid

BROKER  = 'devmonsvr01:61613'
QUEUE   = '/queue/prod.alerts'
LOGFILE = '/tmp/alert-api.log'

Version = "1.2 05/03/2012"
Debug = False

# Extend JSON Encoder to support ISO 8601 format dates
class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        else:
            return json.JSONEncoder.default(self, obj)

def main():

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s alert-api[%(process)d] %(levelname)s Thread-%(thread)d - %(message)s", filename=LOGFILE, filemode='a')

    callback = None

    # cgiform = cgi.FieldStorage()
    data = sys.stdin.read()
    alert = json.loads(data)

    for e in os.environ:
        logging.info('%s: %s', e, os.environ[e])

    status = dict()
    start = time.time()
    status['response'] = dict()
    status['response']['status'] = 'failed' # assume 'failed', unless a response overwrites with 'ok'

    # if 'REQUEST_URI' in os.environ and 'REQUEST_METHOD' in os.environ:

    if os.environ['REQUEST_URI'].startswith('/alerta/api/v1/alerts/alert.json') and os.environ['REQUEST_METHOD'] == 'POST':

        # REQUEST_URI: /alerta/api/v1/alerts/alert.json

        logging.info('POST')

        alertid = str(uuid.uuid4()) # random UUID
        alert['id']          = alertid
        alert['summary']     = '%s - %s %s is %s on %s %s' % (alert['environment'], alert['severity'], alert['event'], alert['value'], alert['service'], os.uname()[1])
        alert['createTime']  = datetime.datetime.now().isoformat()
        alert['origin']      = 'alert-api/%s' % os.uname()[1]


        headers = dict()
        headers['type'] = "text"
        headers['correlation-id'] = alertid
                
        logging.info('ALERT: %s', json.dumps(alert))

        broker, port = BROKER.split(':')
        stomp = Stomp(broker, int(port))
        try:
            stomp.connect()
        except Exception, e:
            logging.error('ERROR: Could not connect to to broker %s - %s', BROKER, e)
            sys.exit(1)
        try:
            stomp.send(QUEUE, json.dumps(alert), headers)
        except Exception, e:
            logging.error('ERROR: Failed to send alert to broker %s - %s', BROKER, e)
            sys.exit(1)
        stomp.disconnect()
        status['response']['id'] = alertid

        diff = time.time() - start
        status['response']['status'] = 'ok'
        status['response']['time'] = "%.3f" % diff
        status['response']['localTime'] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        content = json.dumps(status, cls=DateEncoder)
        if callback is not None:
            content = '%s(%s);' % (callback, content)

        # logging.debug('API >>> %s', content)

        print "Content-Type: application/javascript; charset=utf-8"
        print "Content-Length: %s" % len(content)
        print "Expires: -1"
        print "Cache-Control: no-cache"
        print "Pragma: no-cache"
        print ""
        print content

if __name__ == '__main__':
    main()
