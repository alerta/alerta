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

__version__ = '1.0'

BROKER_LIST  = [('localhost', 61613)] # list of brokers for failover
ALERT_QUEUE  = '/queue/alerts'
EXPIRATION_TIME = 600 # seconds = 10 minutes

URLFILE = '/opt/alerta/conf/alert-urlmon.yaml'
LOGFILE = '/var/log/alerta/alert-urlmon.log'
PIDFILE = '/var/run/alerta/alert-urlmon.pid'

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

_check_rate   = 30             # Check rate of alerts

# Global variables
urls = dict()

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
            warn_thold = 20 # ms
            crit_thold = 1000 # ms

            response = ''
            status = None

            # print(item)
            start = time.time()

            post = item.get('post', None)
            # print "post = %s" % (post)

            headers = dict()
            if 'headers' in item:
                headers = dict(item['headers'])
            # print "headers = %s" % (headers)

            try:
                if post:
                    req = urllib2.Request(item['url'], json.dumps(post), headers=headers)
                else: 
                    req = urllib2.Request(item['url'], headers=headers)
                response = urllib2.urlopen(req)
            except urllib2.URLError, e:
                if hasattr(e, 'reason'):
                    reason = e.reason
                elif hasattr(e, 'code'):
                    status = e.code
            else:
                rtt = int(time.time() - start)
                status = response.getcode()
                body = response.read()
                logging.debug("URL: %s, Status: %d, Round-Trip Time: %dms", item['url'], status, rtt)

            if status == 200:
                event = 'WebsiteStatus'
                severity = 'NORMAL'
                value = 'OK %dms' % rtt
                descrStr = 'Website available and responding within RT thresholds'
                if search_string:
                    found = False
                    for line in body.split('\n'):
                        m = re.search(search_string, line)
                        if m:
                            found = True
                            logging.debug("Regex: Found %s in %s", search_string, line)
                            break
                    if not found:
                        event = 'WebsiteStatus'
                        severity = 'MINOR'
                        value = 'RegexFailed'
                        descrStr = 'Website available but pattern "%s" not found' % (search_string)
                elif rule:
                    if headers['Content-type'] == 'application/json':
                        body = json.loads(body)
                    try:
                        eval(rule)
                    except:
                        event = 'WebsiteStatus'
                        severity = 'MINOR'
                        value = 'EvalFailed'
                        descrStr = 'Website available but rule evaluation failed (%s)' % (rule)
                if rtt > crit_thold:
                    event = 'WebsiteStatus'
                    severity = 'CRITICAL'
                    value = 'Slow %dms' % rtt
                    descrStr = 'Website available but exceeding critical RT thresholds of %dms' % (crit_thold)
                elif rtt > warn_thold:
                    event = 'WebsiteStatus'
                    severity = 'WARNING'
                    value = 'Slow %dms' % rtt
                    descrStr = 'Website available but exceeding warning RT thresholds of %dms' % (warn_thold)
            elif status is None:
                event = 'WebsiteStatus'
                severity = 'MAJOR'
                value = reason
                descrStr = 'Connection error of %s to %s' % (value, item['url'])
            else:
                event = 'WebsiteStatus'
                severity = 'MINOR'
                value = 'BAD %s' % status
                descrStr = 'HTTP status code was %d' % status

            # print "status %s" % status

            alertid = str(uuid.uuid4()) # random UUID

            headers = dict()
            headers['type'] = "availRTAlert"
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
            alert['type']             = 'availRTAlert'
            alert['tags']             = list()
            alert['summary']          = '%s - %s %s is %s on %s %s' % (item['environment'], severity, event, value, item['service'], item['resource'])
            alert['createTime']       = datetime.datetime.utcnow().isoformat()+'Z'
            alert['origin']           = "alert-urlmon/%s" % os.uname()[1]
            alert['thresholdInfo']    = "%s: RT > %d RT > %d x 1" % (item['url'], warn_thold, crit_thold)

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
