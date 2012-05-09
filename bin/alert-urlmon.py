#!/usr/bin/env python
########################################
#
# alert-urlmon.py - Alert URL Monitor
#
########################################

# TODO
# 1. add basic auth support

import os
import sys
import time
import urllib2
try:
    import json
except ImportError:
    import simplejson
import threading
from Queue import Queue
import yaml
import stomp
import datetime
import logging
import uuid
import re
from BaseHTTPServer import BaseHTTPRequestHandler as BHRH
HTTP_RESPONSES = dict([(k, v[0]) for k, v in BHRH.responses.items()])

__version__ = '1.2'

BROKER_LIST  = [('localhost', 61613)] # list of brokers for failover
ALERT_QUEUE  = '/queue/alerts'
EXPIRATION_TIME = 600 # seconds = 10 minutes

URLFILE = '/opt/alerta/conf/alert-urlmon.yaml'
LOGFILE = '/var/log/alerta/alert-urlmon.log'
PIDFILE = '/var/run/alerta/alert-urlmon.pid'

NUM_THREADS = 5
GMETRIC_CMD = '/usr/bin/gmetric'
GMETRIC_OPTIONS = '--spoof urlmon:urlmon --conf /etc/ganglia/alerta/gmond-alerta.conf'

os.environ['http_proxy'] = 'http://proxy.gul3.gnl:3128/'
os.environ['https_proxy'] = 'http://proxy.gul3.gnl:3128/'

HTTP_ALERTS = [
    'HttpConnectionError',
    'HttpServerError',
    'HttpClientError',
    'HttpRedirection',
    'HttpContentError',
    'HttpResponseSlow',
    'HttpResponseOK',
]

# Add missing responses
HTTP_RESPONSES[102] = 'Processing'
HTTP_RESPONSES[207] = 'Multi-Status'
HTTP_RESPONSES[422] = 'Unprocessable Entity'
HTTP_RESPONSES[423] = 'Locked'
HTTP_RESPONSES[424] = 'Failed Dependency'
HTTP_RESPONSES[506] = 'Variant Also Negotiates'
HTTP_RESPONSES[507] = 'Insufficient Storage'
HTTP_RESPONSES[510] = 'Not Extended'

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

_check_rate   = 60             # Check rate of alerts

# Global variables
urls = dict()
queue = Queue()

currentCount  = dict()
currentState  = dict()
previousSeverity = dict()

# Do not follow redirects
class NoRedirection(urllib2.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        result = urllib2.HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)
        result.status = code
        result.code = code
        return result

    http_error_301 = http_error_303 = http_error_307 = http_error_302

class WorkerThread(threading.Thread):

    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.input_queue = queue

    def run(self):
        global conn

        while True:
            item = self.input_queue.get()
            if item is None:
                break

            # defaults
            search_string = item.get('search', None)
            rule = item.get('rule', None)
            warn_thold = item.get('warning', 5000)  # ms
            crit_thold = item.get('critical', 10000) # ms
            post = item.get('post', None)

            logging.info('%s checking %s', self.getName(), item['url'])

            response = ''
            code = None
            status = None

            start = time.time()

            headers = dict()
            if 'headers' in item:
                headers = dict(item['headers'])

            opener = urllib2.build_opener(NoRedirection())
            urllib2.install_opener(opener)

            try:
                if post:
                    req = urllib2.Request(item['url'], json.dumps(post), headers=headers)
                else: 
                    req = urllib2.Request(item['url'], headers=headers)
                response = urllib2.urlopen(req)
            except ValueError, e:
                logging.error('Request failed: %s', e)
                continue
            except urllib2.URLError, e:
                if hasattr(e, 'reason'):
                    reason = e.reason
                elif hasattr(e, 'code'):
                    code = e.code
            else:
                code = response.getcode()
                body = response.read()

            rtt = int((time.time() - start) * 1000) # round-trip time

            try:
                status = HTTP_RESPONSES[code]
            except KeyError:
                status = 'unused'

            if code is None:
                event = 'HttpConnectionError'
                severity = 'MAJOR'
                value = reason
                descrStr = 'Connection error of %s to %s' % (value, item['url'])
            elif code >= 500:
                event = 'HttpServerError'
                severity = 'MAJOR'
                value = '%s (%d)' % (status, code)
                descrStr = 'HTTP server responded with status code %d in %dms' % (code, rtt)
            elif code >= 400:
                event = 'HttpClientError'
                severity = 'MINOR'
                value = '%s (%d)' % (status, code)
                descrStr = 'HTTP server responded with status code %d in %dms' % (code, rtt)
            elif code >= 300:
                event = 'HttpRedirection'
                severity = 'MINOR'
                value = '%s (%d)' % (status, code)
                descrStr = 'HTTP server responded with status code %d in %dms' % (code, rtt)
            elif code >= 200:
                event = 'HttpResponseOK'
                severity = 'NORMAL'
                value = '%s (%d)' % (status, code)
                descrStr = 'HTTP server responded with status code %d in %dms' % (code, rtt)
                if rtt > crit_thold:
                    event = 'HttpResponseSlow'
                    severity = 'CRITICAL'
                    value = '%dms' % rtt
                    descrStr = 'Website available but exceeding critical RT thresholds of %dms' % (crit_thold)
                elif rtt > warn_thold:
                    event = 'HttpResponseSlow'
                    severity = 'WARNING'
                    value = '%dms' % rtt
                    descrStr = 'Website available but exceeding warning RT thresholds of %dms' % (warn_thold)
                if search_string:
                    logging.debug('Searching for %s', search_string)
                    found = False
                    for line in body.split('\n'):
                        m = re.search(search_string, line)
                        if m:
                            found = True
                            logging.debug("Regex: Found %s in %s", search_string, line)
                            break
                    if not found:
                        event = 'HttpContentError'
                        severity = 'MINOR'
                        value = 'Search failed'
                        descrStr = 'Website available but pattern "%s" not found' % (search_string)
                elif rule:
                    logging.debug('Evaluating rule %s', rule)
                    if 'Content-type' in headers and headers['Content-type'] == 'application/json':
                        body = json.loads(body)
                    try:
                        eval(rule)
                    except:
                        logging.error('Could not evaluate rule %s', rule)
                    else:
                        if not eval(rule):
                            event = 'HttpContentError'
                            severity = 'MINOR'
                            value = 'Rule failed'
                            descrStr = 'Website available but rule evaluation failed (%s)' % (rule)
            elif code >= 100:
                event = 'HttpInformational'
                severity = 'NORMAL'
                value = '%s (%d)' % (status, code)
                descrStr = 'HTTP server responded with status code %d in %dms' % (code, rtt)

            logging.debug("URL: %s, Status: %s (%d), Round-Trip Time: %dms -> %s", item['url'], status, code, rtt, event)

            # Forward metric data to Ganglia
            if code < 300:
                avail = 100.0   # 1xx, 2xx -> 100% available
            else:
                avail = 0.0

            gmetric_cmd = "%s --name availability-%s --value %.1f --type float --units \" \" --slope both --group %s %s" % (
                GMETRIC_CMD, item['resource'], avail, item['service'], GMETRIC_OPTIONS)
            logging.debug("%s", gmetric_cmd)
            os.system("%s" % gmetric_cmd)

            gmetric_cmd = "%s --name response_time-%s --value %d --type uint16 --units ms --slope both --group %s %s" % (
                GMETRIC_CMD, item['resource'], rtt, item['service'], GMETRIC_OPTIONS)
            logging.debug("%s", gmetric_cmd)
            os.system("%s" % gmetric_cmd)

            # Set necessary state variables if currentState is unknown
            res = (item['environment'] + '.' + item['service'] + '.' + item['resource']).lower()
            if (res, event) not in currentState:
                currentState[(res, event)] = severity
                currentCount[(res, event, severity)] = 0
                previousSeverity[(res, event)] = severity

            if currentState[(res, event)] != severity:                                                          # Change of threshold state
                currentCount[(res, event, severity)] = currentCount.get((res, event, severity), 0) + 1
                currentCount[(res, event, currentState[(res, event)])] = 0                                      # zero-out previous sev counter
                currentState[(res, event)] = severity
            elif currentState[(res, event)] == severity:                                                        # Threshold state has not changed
                currentCount[(res, event, severity)] += 1

            logging.debug('currentState = %s, currentCount = %d', currentState[(res, event)], currentCount[(res, event, severity)])

            # Determine if should send a repeat alert
            repeat = (currentCount[(res, event, severity)] - item.get('count', 1)) % item.get('repeat', 1) == 0

            logging.debug('Send alert if prevSev %s != %s AND thresh %d == %s', previousSeverity[(res, event)], severity, currentCount[(res, event, severity)], item.get('count', 1))
            logging.debug('Send repeat alert = %s (%d - %d %% %d)', repeat, currentCount[(res, event, severity)], item.get('count', 1), item.get('repeat', 1))

            # Determine if current threshold count requires an alert
            if ((previousSeverity[(res, event)] != severity and currentCount[(res, event, severity)] == item.get('count', 1))
                or (previousSeverity[(res, event)] == severity and repeat)):

                alertid = str(uuid.uuid4()) # random UUID

                headers = dict()
                headers['type']           = "serviceAlert"
                headers['correlation-id'] = alertid
                headers['persistent']     = 'true'
                headers['expires']        = int(time.time() * 1000) + EXPIRATION_TIME * 1000

                # standard alert info
                alert = dict()
                alert['id']               = alertid
                alert['resource']         = (item['environment'] + '.' + item['service'] + '.' + item['resource']).lower()
                alert['event']            = event
                alert['group']            = 'Web'
                alert['value']            = value
                alert['severity']         = severity
                alert['severityCode']     = SEVERITY_CODE[severity]
                alert['environment']      = item['environment']
                alert['service']          = item['service']
                alert['text']             = descrStr
                alert['type']             = 'serviceAlert'
                alert['tags']             = list()
                alert['summary']          = '%s - %s %s is %s on %s %s' % (item['environment'], severity, event, value, item['service'], item['resource'])
                alert['createTime']       = datetime.datetime.utcnow().isoformat()+'Z'
                alert['origin']           = "alert-urlmon/%s" % os.uname()[1]
                alert['thresholdInfo']    = "%s: RT > %d RT > %d x 1" % (item['url'], warn_thold, crit_thold)
                alert['correlatedEvents'] = HTTP_ALERTS

                logging.info('%s : %s', alertid, json.dumps(alert))

                try:
                    conn.send(json.dumps(alert), headers, destination=ALERT_QUEUE)
                except Exception, e:
                    logging.error('Failed to send alert to broker %s', e)
                    sys.exit(1) # XXX - do I really want to exit here???
                broker = conn.get_host_and_port()
                logging.info('%s : Alert sent to %s:%s', alertid, broker[0], str(broker[1]))

                # Keep track of previous severity
                previousSeverity[(res, event)] = severity

            self.input_queue.task_done()

        self.input_queue.task_done()
        return

# Initialise Rules
def init_urls():
    global urls
    logging.info('Loading URLs...')
    try:
        urls = yaml.load(open(URLFILE))
    except Exception, e:
        logging.error('Failed to load URLs: %s', e)
    logging.info('Loaded %d URLs OK', len(urls))

def main():
    global urls, conn

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s alert-urlmon[%(process)d] %(levelname)s - %(message)s", filename=LOGFILE)
    logging.info('Starting up URL monitor version %s', __version__)

    # Write pid file
    if os.path.isfile(PIDFILE):
        logging.error('%s already exists, exiting', PIDFILE)
        sys.exit(1)
    else:
        file(PIDFILE, 'w').write(str(os.getpid()))

    # Connect to message broker
    logging.info('Connect to broker')
    try:
        conn = stomp.Connection(BROKER_LIST)
        conn.start()
        conn.connect(wait=True)
    except Exception, e:
        logging.error('Stomp connection error: %s', e)
        sys.exit(1)

    # Initialiase alert rules
    init_urls()
    url_mod_time = os.path.getmtime(URLFILE)

    # Start worker threads
    for i in range(NUM_THREADS):
        w = WorkerThread(queue)
        w.start()
        logging.info('Starting thread: %s', w.getName())

    while True:
        try:
            # Read (or re-read) urls as necessary
            if os.path.getmtime(URLFILE) != url_mod_time:
                init_urls()
                url_mod_time = os.path.getmtime(URLFILE)

            for url in urls:
                queue.put(url)

            # XXX - uncomment following line if we should wait the on queue until everything has been processed
            # queue.join()

            logging.info('URL check is sleeping %d seconds', _check_rate)
            time.sleep(_check_rate)

        except (KeyboardInterrupt, SystemExit):
            conn.disconnect()
            for i in range(NUM_THREADS):
                queue.put(None)
            w.join()
            os.unlink(PIDFILE)
            sys.exit(0)

if __name__ == '__main__':
    main()
