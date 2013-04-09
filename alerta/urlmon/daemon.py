
import time
import urllib2
import json
import threading
import Queue
import re
from BaseHTTPServer import BaseHTTPRequestHandler as BHRH

import yaml

HTTP_RESPONSES = dict([(k, v[0]) for k, v in BHRH.responses.items()])

from alerta.common import log as logging, severity_code
from alerta.common import config
from alerta.alert import Alert, Heartbeat
from alerta.common.mq import Messaging, MessageHandler
from alerta.common.daemon import Daemon
from alerta.common.dedup import DeDup
from alerta.common.ganglia import Gmetric

Version = '2.0.1'

LOG = logging.getLogger(__name__)
CONF = config.CONF

_WARN_THRESHOLD = 2000  # ms
_CRIT_THRESHOLD = 5000  # ms

_REQUEST_TIMEOUT = 15  # seconds

_GMETRIC_SEND = True

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

    def __init__(self, mq, queue, dedup):

        threading.Thread.__init__(self)
        LOG.debug('Initialising %s...', self.getName())

        self.currentCount = {}
        self.currentState = {}
        self.previousEvent = {}

        self.queue = queue   # internal queue
        self.mq = mq               # message broker
        self.dedup = dedup
        
    def run(self):

        while True:
            LOG.debug('Waiting on input queue...')
            check = self.queue.get()

            if not check:
                LOG.info('%s is shutting down.', self.getName())
                break

            # TODO(nsatterl): add to system defaults
            search_string = check.get('search', None)
            rule = check.get('rule', None)
            warn_thold = check.get('warning', _WARN_THRESHOLD)
            crit_thold = check.get('critical', _CRIT_THRESHOLD)
            post = check.get('post', None)

            LOG.info('%s checking %s', self.getName(), check['url'])
            start = time.time()

            if 'headers' in check:
                headers = dict(check['headers'])
            else:
                headers = dict()

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
                    code = None
                elif hasattr(e, 'code'):
                    reason = None
                    code = e.code
            else:
                code = response.getcode()
                body = response.read()

            rtt = int((time.time() - start) * 1000)  # round-trip time

            try:
                status = HTTP_RESPONSES[code]
            except KeyError:
                status = 'undefined'

            if not code:
                event = 'HttpConnectionError'
                severity = severity_code.MAJOR
                value = reason
                text = 'Error during connection or data transfer (timeout=%d).' % _REQUEST_TIMEOUT
            elif code >= 500:
                event = 'HttpServerError'
                severity = severity_code.MAJOR
                value = '%s (%d)' % (status, code)
                text = 'HTTP server responded with status code %d in %dms' % (code, rtt)
            elif code >= 400:
                event = 'HttpClientError'
                severity = severity_code.MINOR
                value = '%s (%d)' % (status, code)
                text = 'HTTP server responded with status code %d in %dms' % (code, rtt)
            elif code >= 300:
                event = 'HttpRedirection'
                severity = severity_code.MINOR
                value = '%s (%d)' % (status, code)
                text = 'HTTP server responded with status code %d in %dms' % (code, rtt)
            elif code >= 200:
                event = 'HttpResponseOK'
                severity = severity_code.NORMAL
                value = '%s (%d)' % (status, code)
                text = 'HTTP server responded with status code %d in %dms' % (code, rtt)
                if rtt > crit_thold:
                    event = 'HttpResponseSlow'
                    severity = severity_code.CRITICAL
                    value = '%dms' % rtt
                    text = 'Website available but exceeding critical RT thresholds of %dms' % crit_thold
                elif rtt > warn_thold:
                    event = 'HttpResponseSlow'
                    severity = severity_code.WARNING
                    value = '%dms' % rtt
                    text = 'Website available but exceeding warning RT thresholds of %dms' % warn_thold
                if search_string and body:
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
                        severity = severity_code.MINOR
                        value = 'Search failed'
                        text = 'Website available but pattern "%s" not found' % search_string
                elif rule and body:
                    LOG.debug('Evaluating rule %s', rule)
                    if 'Content-type' in headers and headers['Content-type'] == 'application/json':
                        body = json.loads(body)
                    try:
                        eval(rule)  # assumes request body in variable called 'body'
                    except (SyntaxError, NameError, ZeroDivisionError), e:
                        LOG.error('Could not evaluate rule %s: %s', rule, e)
                    except Exception, e:
                        LOG.error('Could not evaluate rule %s: %s', rule, e)
                    else:
                        if not eval(rule):
                            event = 'HttpContentError'
                            severity = severity_code.MINOR
                            value = 'Rule failed'
                            text = 'Website available but rule evaluation failed (%s)' % rule
            elif code >= 100:
                event = 'HttpInformational'
                severity = severity_code.NORMAL
                value = '%s (%d)' % (status, code)
                text = 'HTTP server responded with status code %d in %dms' % (code, rtt)
            else:
                event = 'HttpUnknownError'
                severity = severity_code.WARNING
                value = 'UNKNOWN'
                text = 'HTTP request resulted in an unhandled error.'

            LOG.debug("URL: %s, Status: %s (%s), Round-Trip Time: %dms -> %s", check['url'], status, code, rtt,
                      event)

            # Forward metric data to Ganglia
            if code and code < 300:
                avail = 100.0   # 1xx, 2xx -> 100% available
            else:
                avail = 0.0

            if _GMETRIC_SEND:
                g = Gmetric()
                g.metric_send('availability-%s' % check['resource'], '%.1f' % avail, 'float',
                              units='%', group=','.join(check['service']), spoof=CONF.gmetric_spoof)
                g.metric_send('response_time-%s' % check['resource'], '%d' % rtt, 'uint16',
                              units='ms', group=','.join(check['service']), spoof=CONF.gmetric_spoof)

            resource = check['resource']
            correlate = _HTTP_ALERTS
            group = 'Web'
            environment = check['environment']
            service = check['service']
            text = text
            tags = check.get('tags', list())
            threshold_info = "%s : RT > %d RT > %d x %s" % (check['url'], warn_thold, crit_thold, check.get('count', 1))

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

            if self.dedup.is_send(urlmonAlert):
                self.mq.send(urlmonAlert)

            self.queue.task_done()
            LOG.info('%s check complete.', self.getName())

        self.queue.task_done()


class UrlmonMessage(MessageHandler):

    def __init__(self, mq):
        self.mq = mq
        MessageHandler.__init__(self)

    def on_disconnected(self):
        self.mq.reconnect()


class UrlmonDaemon(Daemon):

    def run(self):

        self.running = True

        # Create internal queue
        self.queue = Queue.Queue()

        # Connect to message queue
        self.mq = Messaging()
        self.mq.connect(callback=UrlmonMessage(self.mq))

        self.dedup = DeDup()

        # Initialiase alert rules
        urls = init_urls()

        # Start worker threads
        LOG.debug('Starting %s worker threads...', CONF.server_threads)
        for i in range(CONF.server_threads):
            w = WorkerThread(self.mq, self.queue, self.dedup)
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





