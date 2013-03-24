import os
import time
import urllib2
import json
import threading
import Queue
import re
from BaseHTTPServer import BaseHTTPRequestHandler as BHRH

import yaml

HTTP_RESPONSES = dict([(k, v[0]) for k, v in BHRH.responses.items()])

from alerta.common import log as logging
from alerta.common import config
from alerta.alert import Alert, Heartbeat
from alerta.common.mq import Messaging
from alerta.common.daemon import Daemon

Version = '2.0.0'

LOG = logging.getLogger(__name__)
CONF = config.CONF

_REQUEST_TIMEOUT = 15  # seconds

_HTTP_ALERTS = [
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


# Initialise Rules
def init_urls():

    urls = list()
    LOG.info('Loading URLs...')
    try:
        urls = yaml.load(open(CONF.yaml_config))
    except Exception, e:
        LOG.error('Failed to load URLs: %s', e)
    LOG.info('Loaded %d URLs OK', len(urls))

    return urls


# Do not follow redirects
class NoRedirection(urllib2.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        result = urllib2.HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)
        result.status = code
        result.code = code
        return result

    http_error_301 = http_error_303 = http_error_307 = http_error_302


class WorkerThread(threading.Thread):

    def __init__(self, mq, queue):

        threading.Thread.__init__(self)
        LOG.debug('Initialising %s...', self.getName())

        self.currentCount = {}
        self.currentState = {}
        self.previousEvent = {}

        self.input_queue = queue   # internal queue
        self.mq = mq               # message broker

    def run(self):

        while True:
            LOG.debug('Waiting on input queue...')
            check = self.input_queue.get()

            if not check:
                LOG.info('%s is shutting down.', self.getName())
                break

            # TODO(nsatterl): add to system defaults
            search_string = check.get('search', None)
            rule = check.get('rule', None)
            warn_thold = check.get('warning', 2000)  # ms
            crit_thold = check.get('critical', 5000) # ms
            post = check.get('post', None)

            LOG.info('%s checking %s', self.getName(), check['url'])

            response = ''
            code = None
            status = None

            start = time.time()

            headers = dict()
            if 'headers' in check:
                headers = dict(check['headers'])

            username = check.get('username', None)
            password = check.get('password', None)
            realm = check.get('realm', None)
            uri = check.get('uri', None)

            proxy = check.get('proxy', False)
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
                    req = urllib2.Request(check['url'], json.dumps(post), headers=headers)
                else:
                    req = urllib2.Request(check['url'], headers=headers)
                response = urllib2.urlopen(req, None, _REQUEST_TIMEOUT)
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
                descrStr = 'Error during connection or data transfer (timeout=%d).' % _REQUEST_TIMEOUT
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
                    descrStr = 'Website available but exceeding critical RT thresholds of %dms' % crit_thold
                elif rtt > warn_thold:
                    event = 'HttpResponseSlow'
                    severity = 'WARNING'
                    value = '%dms' % rtt
                    descrStr = 'Website available but exceeding warning RT thresholds of %dms' % warn_thold
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
                        descrStr = 'Website available but pattern "%s" not found' % search_string
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
                            descrStr = 'Website available but rule evaluation failed (%s)' % rule
            elif code >= 100:
                event = 'HttpInformational'
                severity = 'NORMAL'
                value = '%s (%d)' % (status, code)
                descrStr = 'HTTP server responded with status code %d in %dms' % (code, rtt)

            LOG.debug("URL: %s, Status: %s (%s), Round-Trip Time: %dms -> %s", check['url'], status, code, rtt,
                      event)

            # Forward metric data to Ganglia
            if code and code < 300:
                avail = 100.0   # 1xx, 2xx -> 100% available
            else:
                avail = 0.0

            # if GMETRIC_SEND:
            #     gmetric_cmd = "%s --name availability-%s --value %.1f --type float --units \" \" --slope both --group %s %s" % (
            #         GMETRIC_CMD, check['resource'], avail, ','.join(check['service']),
            #         GMETRIC_OPTIONS) # XXX - gmetric doesn't support multiple groups
            #     LOG.debug("%s", gmetric_cmd)
            #     os.system("%s" % gmetric_cmd)
            # 
            #     gmetric_cmd = "%s --name response_time-%s --value %d --type uint16 --units ms --slope both --group %s %s" % (
            #         GMETRIC_CMD, check['resource'], rtt, ','.join(check['service']), GMETRIC_OPTIONS)
            #     LOG.debug("%s", gmetric_cmd)
            #     os.system("%s" % gmetric_cmd)

            # Set necessary state variables if currentState is unknown
            res = check['resource']
            if (res) not in self.currentState:
                self.currentState[(res)] = event
                self.currentCount[(res, event)] = 0
                self.previousEvent[(res)] = event

            if self.currentState[
                (res)] != event:                                                          # Change of threshold state
                self.currentCount[(res, event)] = self.currentCount.get((res, event), 0) + 1
                self.currentCount[(res, self.currentState[
                    (res)])] = 0                                          # zero-out previous event counter
                self.currentState[(res)] = event
            elif self.currentState[(
                res)] == event:                                                        # Threshold state has not changed
                self.currentCount[(res, event)] += 1

            LOG.debug('currentState = %s, currentCount = %d', self.currentState[(res)], self.currentCount[(res, event)])

            # Determine if should send a repeat alert
            if self.currentCount[(res, event)] < check.get('count', 1):
                repeat = False
                LOG.debug('Send repeat alert = %s (curr %s < threshold %s)', repeat, self.currentCount[(res, event)],
                          check.get('count', 1))
            else:
                repeat = (self.currentCount[(res, event)] - check.get('count', 1)) % check.get('repeat', 1) == 0
                LOG.debug('Send repeat alert = %s (%d - %d %% %d)', repeat, self.currentCount[(res, event)],
                          check.get('count', 1), check.get('repeat', 1))

            LOG.debug('Send alert if prevEvent %s != %s AND thresh %d == %s', self.previousEvent[(res)], event,
                      self.currentCount[(res, event)], check.get('count', 1))

            # Determine if current threshold count requires an alert
            if ((self.previousEvent[(res)] != event and self.currentCount[(res, event)] == check.get('count', 1))
                or (self.previousEvent[(res)] == event and repeat)):

                resource = check['resource']
                correlate = _HTTP_ALERTS
                group = 'Web'
                environment = check['environment']
                service = check['service']
                text = descrStr
                tags = check.get('tags', list())
                threshold_info = "%s : RT > %d RT > %d x %s" % (
                    check['url'], warn_thold, crit_thold, check.get('count', 1))

                urlmonAlert = Alert(
                    resource=resource,
                    event=event,
                    correlate=correlate,
                    group=group,
                    value=value,
                    severity=severity,
                    environment=environment,
                    service=service,
                    text=text,
                    event_type='serviceAlert',
                    tags=tags,
                    threshold_info=threshold_info,
                )
                self.mq.send(urlmonAlert)

                # Keep track of previous event
                self.previousEvent[(res)] = event

            self.input_queue.task_done()
            LOG.info('%s check complete.', self.getName())

        self.input_queue.task_done()


class UrlmonDaemon(Daemon):

    def run(self):

        self.running = True

        # Create internal queue
        self.queue = Queue.Queue()

        # Connect to message queue
        self.mq = Messaging()
        self.mq.connect()

        # Initialiase alert rules
        urls = init_urls()

        # Start worker threads
        LOG.debug('Starting %s worker threads...', CONF.server_threads)
        for i in range(CONF.server_threads):
            w = WorkerThread(self.mq, self.queue)
            try:
                w.start()
            except Exception, e:
                LOG.error('Worker thread #%s did not start: %s', i, e)
                continue
            LOG.info('Started worker thread: %s', w.getName())

        while not self.shuttingdown:
            try:
                for url in urls:
                    self.queue.put(url)

                LOG.debug('Send heartbeat...')
                heartbeat = Heartbeat(version=Version)
                self.mq.send(heartbeat)

                LOG.info('URL check queue length is %d', self.queue.qsize())

                time.sleep(CONF.loop_every)

            except (KeyboardInterrupt, SystemExit):
                self.shuttingdown = True

        LOG.info('Shutdown request received...')
        self.running = False

        for i in range(CONF.server_threads):
            self.queue.put(None)
        w.join()

        LOG.info('Disconnecting from message broker...')
        self.mq.disconnect()





