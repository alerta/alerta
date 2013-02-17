#!/usr/bin/env python
########################################
#
# alerta-app.py - Alerter New Alert API
#
########################################

import os
import sys
try:
    import json
except ImportError:
    import simplejson as json
import time
import datetime
import stomp
import urlparse
import logging
import uuid
import re

__version__ = '1.4.1'

BROKER_LIST  = [('localhost', 61613)] # list of brokers for failover
ALERT_QUEUE  = '/queue/alerts'
EXPIRATION_TIME = 600 # seconds = 10 minutes

LOGFILE = '/var/log/alerta/alert-app.log'

VALID_SEVERITY    = [ 'CRITICAL', 'MAJOR', 'MINOR', 'WARNING', 'NORMAL', 'INFORM', 'DEBUG' ]
VALID_ENVIRONMENT = [ 'PROD', 'REL', 'QA', 'TEST', 'CODE', 'STAGE', 'DEV', 'LWP','INFRA' ]

SEVERITY_CODE = {
    # ITU RFC5674 -> Syslog RFC5424
    'CRITICAL':       1, # Alert
    'MAJOR':          2, # Crtical
    'MINOR':          3, # Error
    'WARNING':        4, # Warning
    'NORMAL':         5, # Notice
    'INFORM':         6, # Informational
    'DEBUG':          7, # Debug
}

# Extend JSON Encoder to support ISO 8601 format dates
class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.replace(microsecond=0).isoformat() + ".%03dZ" % (obj.microsecond//1000)
        else:
            return json.JSONEncoder.default(self, obj)

def main():

    start = time.time()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s alert-app[%(process)d] %(levelname)s - %(message)s", filename=LOGFILE)
    logging.info('Received HTTP request %s %s' % (os.environ['REQUEST_METHOD'], os.environ['REQUEST_URI']))

    status = dict()
    status['response'] = dict()
    status['response']['status'] = None
    error = 'unknown error'

    for e in os.environ:
       logging.debug('%s: %s', e, os.environ[e])

    # Get HTTP method and any body data
    method = os.environ['REQUEST_METHOD']
    if method in ['PUT', 'POST']:
        try:
            data = json.loads(sys.stdin.read())
        except ValueError, e:
            data = list()
            logging.warning('Failed to get data - %s', e)
            error = 'failed to parse json data in body'

    # Parse RESTful URI
    uri = urlparse.urlsplit(os.environ['REQUEST_URI'])
    form = urlparse.parse_qs(os.environ['QUERY_STRING'])
    request = method + ' ' + uri.path

    m = re.search(r'(PUT|POST) /alerta/api/v1/alerts/alert.json$', request)
    if m:
        alert = data

        # Set any defaults
        if 'severity' not in alert:
            alert['severity'] = 'normal'
        if 'group' not in alert:
            alert['group'] = 'Misc'

        # Check for mandatory attributes
        if 'resource' not in alert:
            error = 'must supply a resource'
        elif 'event' not in alert:
            error = 'must supply event name'
        elif 'value' not in alert:
            error = 'must supply event value'
        elif alert['severity'].upper() not in VALID_SEVERITY:
            error = 'severity must be one of %s' % ', '.join(VALID_SEVERITY)
        elif not all(x in VALID_ENVIRONMENT for x in alert['environment']):
            error = 'must supply one or more environments from %s' % (','.join(VALID_ENVIRONMENT))
        elif 'service' not in alert:
            error = 'must supply one or more service'
        elif 'text' not in alert:
            error = 'must supply alert text'
        else:
            alertid = str(uuid.uuid4()) # random UUID
            createTime = datetime.datetime.utcnow()

            headers = dict()
            headers['type']           = "exceptionAlert"
            headers['correlation-id'] = alertid
            headers['persistent']     = 'true'
            headers['expires']        = int(time.time() * 1000) + EXPIRATION_TIME * 1000

            alert['id']            = alertid
            alert['severity']      = alert['severity'].upper()
            alert['severityCode']  = SEVERITY_CODE[alert['severity']]
            alert['environment']   = [x.upper() for x in alert['environment']]
            alert['type']          = 'exceptionAlert'
            alert['summary']       = '%s - %s %s is %s on %s %s' % (','.join(alert['environment']), alert['severity'].upper(), alert['event'], alert['value'], ','.join(alert['service']), alert['resource'])
            alert['createTime']    = createTime.replace(microsecond=0).isoformat() + ".%03dZ" % (createTime.microsecond//1000)
            alert['origin']        = 'alert-app/%s' % os.uname()[1]

            logging.info('%s : %s', alertid, json.dumps(alert))

            try:
                conn = stomp.Connection(BROKER_LIST)
                conn.start()
                conn.connect(wait=True)
            except Exception, e:
                print >>sys.stderr, "ERROR: Could not connect to broker - %s" % e
                logging.error('Could not connect to broker %s', e)
            try:
                conn.send(json.dumps(alert), headers, destination=ALERT_QUEUE)
            except Exception, e:
                print >>sys.stderr, "ERROR: Failed to send alert to broker - %s " % e
                logging.error('Failed to send alert to broker %s', e)
            broker = conn.get_host_and_port()
            logging.info('%s : Alert sent to %s:%s', alertid, broker[0], str(broker[1]))
            conn.disconnect()

            status['response']['id'] = alertid
            status['response']['status'] = 'ok'

            diff = time.time() - start
            status['response']['time'] = "%.3f" % diff
            status['response']['localTime'] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    if status['response']['status'] == None:

        logging.error('Failed request %s', request)

        diff = time.time() - start
        status['response']['time'] = "%.3f" % diff
        status['response']['status'] = 'error'
        status['response']['message'] = error
        status['response']['localTime'] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        diff = int(diff * 1000)

    content = json.dumps(status, cls=DateEncoder)
    if 'callback' in form:
        content = '%s(%s);' % (form['callback'][0], content)

    print "Content-Type: application/javascript; charset=utf-8"
    print "Content-Length: %s" % len(content)
    print "Expires: -1"
    print "Cache-Control: no-cache"
    print "Pragma: no-cache"
    print ""
    print content

    logging.info('Request %s completed in %sms', request, diff)

if __name__ == '__main__':
    main()
