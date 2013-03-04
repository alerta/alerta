import os
import time
import urllib2
import json
import threading
from Queue import Queue
import datetime
import uuid
import re
from BaseHTTPServer import BaseHTTPRequestHandler as BHRH

import yaml

HTTP_RESPONSES = dict([(k, v[0]) for k, v in BHRH.responses.items()])

from alerta.common import log as logging
from alerta.common import config
from alerta.alert import Alert, Heartbeat
from alerta.common.mq import Messaging, MessageHandler
from alerta.common.daemon import Daemon

Version = '2.0.0'

LOG = logging.getLogger(__name__)
CONF = config.CONF

URLFILE = '/opt/alerta/alerta/alert-urlmon.yaml'

REQUEST_TIMEOUT = 15 # seconds

GMETRIC_SEND = True
GMETRIC_CMD = '/usr/bin/gmetric'
GMETRIC_OPTIONS = '--spoof 10.1.1.1:urlmon --alerta /etc/ganglia/alerta/gmond-alerta.alerta'

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

_check_rate = 60             # Check rate of alerts

# Global variables
urls = dict()
queue = Queue()

currentCount = dict()
currentState = dict()
previousEvent = dict()


# Initialise Rules
def init_urls():
    global urls
    LOG.info('Loading URLs...')
    try:
        urls = yaml.load(open(URLFILE))
    except Exception, e:
        LOG.error('Failed to load URLs: %s', e)
    LOG.info('Loaded %d URLs OK', len(urls))


class UrlmonDaemon(Daemon):
    def run(self):

        self.running = True

        # Connect to message queue
        self.mq = Messaging()
        self.mq.connect()

        # Initialiase alert rules
        init_urls()
        url_mod_time = os.path.getmtime(URLFILE)

        # Start worker threads
        for i in range(CONF.server_threads):
            w = WorkerThread(queue)
            w.start()
            LOG.info('Starting thread: %s', w.getName())

        while not self.shuttingdown:
            try:
                # Read (or re-read) urls as necessary
                if os.path.getmtime(URLFILE) != url_mod_time:
                    init_urls()
                    url_mod_time = os.path.getmtime(URLFILE)

                for url in urls:
                    queue.put(('url', url))
                queue.put(('timestamp', time.time()))

                LOG.debug('Send heartbeat...')
                heartbeat = Heartbeat()
                self.mq.send(heartbeat)

                time.sleep(_check_rate)

                urlmon_qsize = queue.qsize()
                LOG.info('URL check queue length is %d', urlmon_qsize)

                if GMETRIC_SEND:
                    gmetric_cmd = "%s --name urlmon_qsize --value %d --type uint16 --units \" \" --slope both --group urlmon %s" % (
                        GMETRIC_CMD, urlmon_qsize, GMETRIC_OPTIONS)
                    LOG.debug("%s", gmetric_cmd)
                    os.system("%s" % gmetric_cmd)

            except (KeyboardInterrupt, SystemExit):
                self.shuttingdown = True

        LOG.info('Shutdown request received...')
        self.running = False

        for i in range(CONF.server_threads):
            queue.put(('stop', None))
        w.join()

        LOG.info('Disconnecting from message broker...')
        self.mq.disconnect()


class UrlmonMessage(MessageHandler):
    def on_message(self, headers, body):
        LOG.debug("Received: %s", body)


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
            flag, item = self.input_queue.get()
            if flag == 'stop':
                LOG.info('%s is shutting down.', self.getName())
                break
            if flag == 'timestamp':
                urlmon_cycletime = time.time() - item
                LOG.info('Took %d seconds to schedule all checks.', urlmon_cycletime)
                if GMETRIC_SEND:
                    gmetric_cmd = "%s --name urlmon_cycletime --value %d --type uint16 --units seconds --slope both --group urlmon %s" % (
                        GMETRIC_CMD, urlmon_cycletime, GMETRIC_OPTIONS)
                    LOG.debug("%s", gmetric_cmd)
                    os.system("%s" % gmetric_cmd)
                self.input_queue.task_done()
                continue

            # defaults
            search_string = item.get('search', None)
            rule = item.get('rule', None)
            warn_thold = item.get('warning', 2000)  # ms
            crit_thold = item.get('critical', 5000) # ms
            post = item.get('post', None)

            LOG.info('%s checking %s', self.getName(), item['url'])

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
                auth_handler.add_password(realm=realm,
                                          uri=uri,
                                          user=username,
                                          passwd=password)
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
                headers['User-agent'] = 'alert-urlmon/%s Python-urllib/%s' % (Version, urllib2.__version__)

            try:
                if post:
                    req = urllib2.Request(item['url'], json.dumps(post), headers=headers)
                else:
                    req = urllib2.Request(item['url'], headers=headers)
                response = urllib2.urlopen(req, None, REQUEST_TIMEOUT)
            except ValueError, e:
                LOG.error('Request failed: %s', e)
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
                    LOG.debug('Searching for %s', search_string)
                    found = False
                    for line in body.split('\n'):
                        m = re.search(search_string, line)
                        if m:
                            found = True
                            LOG.debug("Regex: Found %s in %s", search_string, line)
                            break
                    if not found:
                        event = 'HttpContentError'
                        severity = 'MINOR'
                        value = 'Search failed'
                        descrStr = 'Website available but pattern "%s" not found' % (search_string)
                elif rule:
                    LOG.debug('Evaluating rule %s', rule)
                    if 'Content-type' in headers and headers['Content-type'] == 'application/json':
                        body = json.loads(body)
                    try:
                        eval(rule)
                    except:
                        LOG.error('Could not evaluate rule %s', rule)
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

            LOG.debug("URL: %s, Status: %s (%s), Round-Trip Time: %dms -> %s", item['url'], status, code, rtt,
                          event)

            # Forward metric data to Ganglia
            if code and code < 300:
                avail = 100.0   # 1xx, 2xx -> 100% available
            else:
                avail = 0.0

            if GMETRIC_SEND:
                gmetric_cmd = "%s --name availability-%s --value %.1f --type float --units \" \" --slope both --group %s %s" % (
                    GMETRIC_CMD, item['resource'], avail, ','.join(item['service']),
                    GMETRIC_OPTIONS) # XXX - gmetric doesn't support multiple groups
                LOG.debug("%s", gmetric_cmd)
                os.system("%s" % gmetric_cmd)

                gmetric_cmd = "%s --name response_time-%s --value %d --type uint16 --units ms --slope both --group %s %s" % (
                    GMETRIC_CMD, item['resource'], rtt, ','.join(item['service']), GMETRIC_OPTIONS)
                LOG.debug("%s", gmetric_cmd)
                os.system("%s" % gmetric_cmd)

            # Set necessary state variables if currentState is unknown
            res = item['resource']
            if (res) not in currentState:
                currentState[(res)] = event
                currentCount[(res, event)] = 0
                previousEvent[(res)] = event

            if currentState[
                (res)] != event:                                                          # Change of threshold state
                currentCount[(res, event)] = currentCount.get((res, event), 0) + 1
                currentCount[(res, currentState[
                    (res)])] = 0                                          # zero-out previous event counter
                currentState[(res)] = event
            elif currentState[(
            res)] == event:                                                        # Threshold state has not changed
                currentCount[(res, event)] += 1

            LOG.debug('currentState = %s, currentCount = %d', currentState[(res)], currentCount[(res, event)])

            # Determine if should send a repeat alert
            if currentCount[(res, event)] < item.get('count', 1):
                repeat = False
                LOG.debug('Send repeat alert = %s (curr %s < threshold %s)', repeat, currentCount[(res, event)],
                              item.get('count', 1))
            else:
                repeat = (currentCount[(res, event)] - item.get('count', 1)) % item.get('repeat', 1) == 0
                LOG.debug('Send repeat alert = %s (%d - %d %% %d)', repeat, currentCount[(res, event)],
                              item.get('count', 1), item.get('repeat', 1))

            LOG.debug('Send alert if prevEvent %s != %s AND thresh %d == %s', previousEvent[(res)], event,
                          currentCount[(res, event)], item.get('count', 1))

            # Determine if current threshold count requires an alert
            if ((previousEvent[(res)] != event and currentCount[(res, event)] == item.get('count', 1))
                or (previousEvent[(res)] == event and repeat)):

                alertid = str(uuid.uuid4()) # random UUID
                createTime = datetime.datetime.utcnow()

                headers = dict()
                headers['type'] = "serviceAlert"
                headers['correlation-id'] = alertid

                # standard alert info
                alert = dict()
                alert['id'] = alertid
                alert['resource'] = item['resource']
                alert['event'] = event
                alert['group'] = 'Web'
                alert['value'] = value
                alert['severity'] = severity
                alert['severityCode'] = SEVERITY_CODE[severity]
                alert['environment'] = item['environment']
                alert['service'] = item['service']
                alert['text'] = descrStr
                alert['type'] = 'serviceAlert'
                alert['tags'] = item.get('tags', list())
                alert['summary'] = '%s - %s %s is %s on %s %s' % (
                ','.join(item['environment']), severity, event, value, ','.join(item['service']), item['resource'])
                alert['createTime'] = createTime.replace(microsecond=0).isoformat() + ".%03dZ" % (
                createTime.microsecond // 1000)
                alert['origin'] = "%s/%s" % (__program__, os.uname()[1])
                alert['thresholdInfo'] = "%s : RT > %d RT > %d x %s" % (
                item['url'], warn_thold, crit_thold, item.get('count', 1))
                alert['timeout'] = DEFAULT_TIMEOUT
                alert['correlatedEvents'] = HTTP_ALERTS

                LOG.info('%s : %s', alertid, json.dumps(alert))

                while not conn.is_connected():
                    LOG.warning('Waiting for message broker to become available')
                    time.sleep(1.0)

                try:
                    conn.send(json.dumps(alert), headers, destination=ALERT_QUEUE)
                    broker = conn.get_host_and_port()
                    LOG.info('%s : Alert sent to %s:%s', alertid, broker[0], str(broker[1]))
                except Exception, e:
                    LOG.error('Failed to send alert to broker %s', e)

                # Keep track of previous event
                previousEvent[(res)] = event

            self.input_queue.task_done()
            LOG.info('%s check complete.', self.getName())

        self.input_queue.task_done()








