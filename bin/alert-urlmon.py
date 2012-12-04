#!/usr/bin/env python
########################################
#
# alert-urlmon.py - Alert URL Monitor
#
########################################

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

__program__ = 'alert-urlmon'
__version__ = '1.5.12'

BROKER_LIST  = [('localhost', 61613)] # list of brokers for failover
ALERT_QUEUE  = '/queue/alerts'

DEFAULT_TIMEOUT = 86400
EXPIRATION_TIME = 600 # seconds = 10 minutes

URLFILE = '/opt/alerta/conf/alert-urlmon.yaml'
LOGFILE = '/var/log/alerta/alert-urlmon.log'
PIDFILE = '/var/run/alerta/alert-urlmon.pid'

REQUEST_TIMEOUT = 15 # seconds
NUM_THREADS = 10

GMETRIC_SEND = True
GMETRIC_CMD = '/usr/bin/gmetric'
GMETRIC_OPTIONS = '--spoof 10.1.1.1:urlmon --conf /etc/ganglia/alerta/gmond-alerta.conf'

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
previousEvent = dict()

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
            flag,item = self.input_queue.get()
            if flag == 'stop':
                logging.info('%s is shutting down.', self.getName())
                break
            if flag == 'timestamp':
                urlmon_cycletime = time.time() - item
                logging.info('Took %d seconds to schedule all checks.', urlmon_cycletime)
                if GMETRIC_SEND:
                    gmetric_cmd = "%s --name urlmon_cycletime --value %d --type uint16 --units seconds --slope both --group urlmon %s" % (
                        GMETRIC_CMD, urlmon_cycletime, GMETRIC_OPTIONS)
                    logging.debug("%s", gmetric_cmd)
                    os.system("%s" % gmetric_cmd)
                self.input_queue.task_done()
                continue

            # defaults
            search_string = item.get('search', None)
            rule = item.get('rule', None)
            warn_thold = item.get('warning', 2000)  # ms
            crit_thold = item.get('critical', 5000) # ms
            post = item.get('post', None)

            logging.info('%s checking %s', self.getName(), item['url'])

            response = ''
            code = None
            status = None

            start = time.time()

            headers = dict()
            if 'headers' in item:
                headers = dict(item['headers'])

            username = item.get('username', None)
            password = item.get('password', None)
            realm = item.get('realm', None)
            uri = item.get('uri', None)

            proxy = item.get('proxy', False)
            if proxy:
                proxy_handler = urllib2.ProxyHandler(proxy)

            if username and password:
                auth_handler = urllib2.HTTPBasicAuthHandler()
                auth_handler.add_password(realm = realm,
                    uri = uri,
                    user = username,
                    passwd = password)
                if proxy:
                    opener = urllib2.build_opener(auth_handler, proxy_handler)
                else:
                    opener = urllib2.build_opener(auth_handler)
            else:
                redir_handler = NoRedirection()
                if proxy:
                    opener = urllib2.build_opener(redir_handler, proxy_handler)
                else:
                    opener = urllib2.build_opener(redir_handler)
            urllib2.install_opener(opener)

            if 'User-agent' not in headers:
                headers['User-agent'] = 'alert-urlmon/%s Python-urllib/%s' % (__version__, urllib2.__version__)

            try:
                if post:
                    req = urllib2.Request(item['url'], json.dumps(post), headers=headers)
                else: 
                    req = urllib2.Request(item['url'], headers=headers)
                response = urllib2.urlopen(req, None, REQUEST_TIMEOUT)
            except ValueError, e:
                logging.error('Request failed: %s', e)
                continue
            except urllib2.URLError, e:
                if hasattr(e, 'reason'):
                    reason = str(e.reason)
                elif hasattr(e, 'code'):
                    code = e.code
            else:
                code = response.getcode()
                body = response.read()

            rtt = int((time.time() - start) * 1000) # round-trip time

            try:
                status = HTTP_RESPONSES[code]
            except KeyError:
                status = 'undefined'

            if code is None:
                event = 'HttpConnectionError'
                severity = 'MAJOR'
                value = reason
                descrStr = 'Error during connection or data transfer (timeout=%d).' % (REQUEST_TIMEOUT)
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

            logging.debug("URL: %s, Status: %s (%s), Round-Trip Time: %dms -> %s", item['url'], status, code, rtt, event)

            # Forward metric data to Ganglia
            if code and code < 300:
                avail = 100.0   # 1xx, 2xx -> 100% available
            else:
                avail = 0.0

            if GMETRIC_SEND:
                gmetric_cmd = "%s --name availability-%s --value %.1f --type float --units \" \" --slope both --group %s %s" % (
                    GMETRIC_CMD, item['resource'], avail, ','.join(item['service']), GMETRIC_OPTIONS) # XXX - gmetric doesn't support multiple groups
                logging.debug("%s", gmetric_cmd)
                os.system("%s" % gmetric_cmd)

                gmetric_cmd = "%s --name response_time-%s --value %d --type uint16 --units ms --slope both --group %s %s" % (
                    GMETRIC_CMD, item['resource'], rtt, ','.join(item['service']), GMETRIC_OPTIONS)
                logging.debug("%s", gmetric_cmd)
                os.system("%s" % gmetric_cmd)

            # Set necessary state variables if currentState is unknown
            res = item['resource']
            if (res) not in currentState:
                currentState[(res)] = event
                currentCount[(res, event)] = 0
                previousEvent[(res)] = event

            if currentState[(res)] != event:                                                          # Change of threshold state
                currentCount[(res, event)] = currentCount.get((res, event), 0) + 1
                currentCount[(res, currentState[(res)])] = 0                                          # zero-out previous event counter
                currentState[(res)] = event
            elif currentState[(res)] == event:                                                        # Threshold state has not changed
                currentCount[(res, event)] += 1

            logging.debug('currentState = %s, currentCount = %d', currentState[(res)], currentCount[(res, event)])

            # Determine if should send a repeat alert
            if currentCount[(res, event)] < item.get('count', 1):
                repeat = False
                logging.debug('Send repeat alert = %s (curr %s < threshold %s)', repeat, currentCount[(res, event)], item.get('count', 1))
            else:
                repeat = (currentCount[(res, event)] - item.get('count', 1)) % item.get('repeat', 1) == 0
                logging.debug('Send repeat alert = %s (%d - %d %% %d)', repeat, currentCount[(res, event)], item.get('count', 1), item.get('repeat', 1))

            logging.debug('Send alert if prevEvent %s != %s AND thresh %d == %s', previousEvent[(res)], event, currentCount[(res, event)], item.get('count', 1))

            # Determine if current threshold count requires an alert
            if ((previousEvent[(res)] != event and currentCount[(res, event)] == item.get('count', 1))
                or (previousEvent[(res)] == event and repeat)):

                alertid = str(uuid.uuid4()) # random UUID
                createTime = datetime.datetime.utcnow()

                headers = dict()
                headers['type']           = "serviceAlert"
                headers['correlation-id'] = alertid

                # standard alert info
                alert = dict()
                alert['id']               = alertid
                alert['resource']         = item['resource']
                alert['event']            = event
                alert['group']            = 'Web'
                alert['value']            = value
                alert['severity']         = severity
                alert['severityCode']     = SEVERITY_CODE[severity]
                alert['environment']      = item['environment']
                alert['service']          = item['service']
                alert['text']             = descrStr
                alert['type']             = 'serviceAlert'
                alert['tags']             = item.get('tags', list())
                alert['summary']          = '%s - %s %s is %s on %s %s' % (','.join(item['environment']), severity, event, value, ','.join(item['service']), item['resource'])
                alert['createTime']       = createTime.replace(microsecond=0).isoformat() + ".%03dZ" % (createTime.microsecond//1000)
                alert['origin']           = "%s/%s" % (__program__, os.uname()[1])
                alert['thresholdInfo']    = "%s : RT > %d RT > %d x %s" % (item['url'], warn_thold, crit_thold, item.get('count', 1))
                alert['timeout']          = DEFAULT_TIMEOUT
                alert['correlatedEvents'] = HTTP_ALERTS

                logging.info('%s : %s', alertid, json.dumps(alert))

                while not conn.is_connected():
                    logging.warning('Waiting for message broker to become available')
                    time.sleep(1.0)

                try:
                    conn.send(json.dumps(alert), headers, destination=ALERT_QUEUE)
                    broker = conn.get_host_and_port()
                    logging.info('%s : Alert sent to %s:%s', alertid, broker[0], str(broker[1]))
                except Exception, e:
                    logging.error('Failed to send alert to broker %s', e)

                # Keep track of previous event
                previousEvent[(res)] = event

            self.input_queue.task_done()
            logging.info('%s check complete.', self.getName())

        self.input_queue.task_done()
        return

class MessageHandler(object):

    def on_error(self, headers, body):
        logging.error('Received an error %s', body)

    def on_disconnected(self):
        global conn

        logging.warning('Connection lost. Attempting auto-reconnect to %s', ALERT_QUEUE)
        conn.start()
        conn.connect(wait=True)
        conn.subscribe(destination=ALERT_QUEUE, ack='auto')

def send_heartbeat():
    global conn

    heartbeatid = str(uuid.uuid4()) # random UUID
    createTime = datetime.datetime.utcnow()

    headers = dict()
    headers['type']           = "heartbeat"
    headers['correlation-id'] = heartbeatid
    # headers['persistent']     = 'false'
    # headers['expires']        = int(time.time() * 1000) + EXPIRATION_TIME * 1000

    heartbeat = dict()
    heartbeat['id']         = heartbeatid
    heartbeat['type']       = "heartbeat"
    heartbeat['createTime'] = createTime.replace(microsecond=0).isoformat() + ".%03dZ" % (createTime.microsecond//1000)
    heartbeat['origin']     = "%s/%s" % (__program__, os.uname()[1])
    heartbeat['version']    = __version__

    try:
        conn.send(json.dumps(heartbeat), headers, destination=ALERT_QUEUE)
        broker = conn.get_host_and_port()
        logging.info('%s : Heartbeat sent to %s:%s', heartbeatid, broker[0], str(broker[1]))
    except Exception, e:
        logging.error('Failed to send heartbeat to broker %s', e)

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

    logging.basicConfig(level=logging.INFO, format="%(asctime)s alert-urlmon[%(process)d] %(threadName)s %(levelname)s - %(message)s", filename=LOGFILE)
    logging.info('Starting up URL monitor version %s', __version__)

    # Write pid file if not already running
    if os.path.isfile(PIDFILE):
        pid = open(PIDFILE).read()
        try:
            os.kill(int(pid), 0)
            logging.error('Process with pid %s already exists, exiting', pid)
            sys.exit(1)
        except OSError:
            pass
    file(PIDFILE, 'w').write(str(os.getpid()))

    # Connect to message broker
    logging.info('Connect to broker')
    try:
        conn = stomp.Connection(
                   BROKER_LIST,
                   reconnect_sleep_increase = 5.0,
                   reconnect_sleep_max = 120.0,
                   reconnect_attempts_max = 20
               )
        conn.set_listener('', MessageHandler())
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
                queue.put(('url',url))
            queue.put(('timestamp', time.time()))

            send_heartbeat()
            time.sleep(_check_rate)

            urlmon_qsize = queue.qsize()
            logging.info('URL check queue length is %d', urlmon_qsize)
            if GMETRIC_SEND:
                gmetric_cmd = "%s --name urlmon_qsize --value %d --type uint16 --units \" \" --slope both --group urlmon %s" % (
                    GMETRIC_CMD, urlmon_qsize, GMETRIC_OPTIONS)
                logging.debug("%s", gmetric_cmd)
                os.system("%s" % gmetric_cmd)

        except (KeyboardInterrupt, SystemExit):
            conn.disconnect()
            for i in range(NUM_THREADS):
                queue.put(('stop',None))
            w.join()
            os.unlink(PIDFILE)
            logging.info('Graceful exit.')
            sys.exit(0)

if __name__ == '__main__':
    main()
