#!/usr/bin/env python
########################################
#
# alert-urlmon.py - Alert URL Monitor
#
########################################

# TODO
# 1. add count and repeat
# 2. make warn and crit threshold configurable
# 3. send RT to ganglia via gmetric (support spoof host)
# 4. support username/password for urban airship
# 5. only send alert on state-change (but fwd to ganglia every time)
# 6. start configurable number of threads

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

__version__ = '1.0'

BROKER_LIST  = [('localhost', 61613)] # list of brokers for failover
ALERT_QUEUE  = '/queue/alerts'
EXPIRATION_TIME = 600 # seconds = 10 minutes

URLFILE = '/opt/alerta/conf/alert-urlmon.yaml'
LOGFILE = '/var/log/alerta/alert-urlmon.log'
PIDFILE = '/var/run/alerta/alert-urlmon.pid'

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

# Do not follow redirects
class NoRedirection(urllib2.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        result = urllib2.HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)
        result.status = code
        result.code = code
        return result

    http_error_301 = http_error_303 = http_error_307 = http_error_302

class WorkerThread(threading.Thread):

    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)
        self.input_queue = Queue()

    def send(self, item):
        self.input_queue.put(item)

    def close(self):
        self.input_queue.put(None)
        self.input_queue.join()

    def run(self):
        global conn

        while True:
            item = self.input_queue.get()
            if item is None:
                break

            # URL check logic
            # 1. get URL  (XXX - support GET, HEAD, POST, PUT, DELETE?)
            # 2. if connection error... 
            #         ALERT = ConnectionError   <- could not fulfill the request
            # 3. if http status code bad...
            #         ALERT = BadStatusCode  <-- non-200 error code
            # 4. if status code 200 but missing search text
            #         ALERT = RegexFailed
            # 5. if status code 200 but RT > warn or crit
            #         ALERT = RespTime <x>ms
            # 6. if status code 200
            #         ALERT = WebStatus OK with response time (fwd RT to ganglia)

            # defaults
            search_string = item.get('search', None)
            rule = item.get('rule', None)
            warn_thold = 200 # ms
            crit_thold = 1000 # ms

            response = ''
            code = None
            status = None

            start = time.time()
            post = item.get('post', None)

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
                rtt = int((time.time() - start) * 1000)
                code = response.getcode()
                body = response.read()

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
                elif rtt > crit_thold:
                    event = 'HttpResponseSlow'
                    severity = 'CRITICAL'
                    value = '%dms' % rtt
                    descrStr = 'Website available but exceeding critical RT thresholds of %dms' % (crit_thold)
                elif rtt > warn_thold:
                    event = 'HttpResponseSlow'
                    severity = 'WARNING'
                    value = '%dms' % rtt
                    descrStr = 'Website available but exceeding warning RT thresholds of %dms' % (warn_thold)
            elif code >= 100:
                event = 'HttpInformational'
                severity = 'NORMAL'
                value = '%s (%d)' % (status, code)
                descrStr = 'HTTP server responded with status code %d in %dms' % (code, rtt)

            logging.debug("URL: %s, Status: %s (%d), Round-Trip Time: %dms -> %s", item['url'], status, code, rtt, event)

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

    # Start worker thread
    w = WorkerThread()
    w.start()

    while True:
        try:

            # Read (or re-read) urls as necessary
            if os.path.getmtime(URLFILE) != url_mod_time:
                init_urls()
                url_mod_time = os.path.getmtime(URLFILE)

            for url in urls:
                w.send(url)

            logging.info('URL check is sleeping %d seconds', _check_rate)
            time.sleep(_check_rate)

        except (KeyboardInterrupt, SystemExit):
            conn.disconnect()
            w.close()
            os.unlink(PIDFILE)
            sys.exit(0)

if __name__ == '__main__':
    main()
