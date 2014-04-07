
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
from alerta.common.alert import Alert
from alerta.common.dedup import DeDup
from alerta.common.heartbeat import Heartbeat
from alerta.common import severity_code
from alerta.common.transform import Transformers
from alerta.common.api import ApiClient
from alerta.common.daemon import Daemon
from alerta.common.graphite import Carbon

__version__ = '3.0.4'

LOG = logging.getLogger(__name__)
CONF = config.CONF

_HTTP_ALERTS = [
    'HttpConnectionError',
    'HttpServerError',
    'HttpClientError',
    'HttpRedirection',
    'HttpContentError',
    'HttpResponseSlow',
    'HttpResponseOK',
    'HttpResponseRegexError',
    'HttpResponseRegexOK'
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
        urls = yaml.load(open(CONF.urlmon_file))
    except Exception, e:
        LOG.error('Failed to load URLs: %s', e)
    LOG.info('Loaded %d URLs OK', len(urls))

    return urls


class WorkerThread(threading.Thread):

    def __init__(self, api, queue, dedup, carbon):

        threading.Thread.__init__(self)
        LOG.debug('Initialising %s...', self.getName())

        self.currentCount = {}
        self.currentState = {}
        self.previousEvent = {}

        self.queue = queue   # internal queue
        self.api = api               # message broker
        self.dedup = dedup
        self.carbon = carbon
        
    def run(self):

        while True:
            LOG.debug('Waiting on input queue...')
            try:
                check, queue_time = self.queue.get()
            except TypeError:
                LOG.info('%s is shutting down.', self.getName())
                break

            if time.time() - queue_time > CONF.loop_every:
                LOG.warning('URL request for %s to %s expired after %d seconds.', check['resource'], check['url'],
                            int(time.time() - queue_time))
                self.queue.task_done()
                continue

            status_regex = check.get('status_regex', None)
            search_string = check.get('search', None)
            rule = check.get('rule', None)
            warn_thold = check.get('warning', CONF.urlmon_slow_warning)
            crit_thold = check.get('critical', CONF.urlmon_slow_critical)
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
                if proxy:
                    opener = urllib2.build_opener(proxy_handler)
                else:
                    opener = urllib2.build_opener()
            urllib2.install_opener(opener)

            if 'User-agent' not in headers:
                headers['User-agent'] = 'alert-urlmon/%s Python-urllib/%s' % (__version__, urllib2.__version__)

            try:
                if post:
                    req = urllib2.Request(check['url'], json.dumps(post), headers=headers)
                else:
                    req = urllib2.Request(check['url'], headers=headers)
                response = urllib2.urlopen(req, None, CONF.urlmon_max_timeout)
            except ValueError, e:
                LOG.error('Request failed: %s', e)
                continue
            except urllib2.URLError, e:
                if hasattr(e, 'reason'):
                    reason = str(e.reason)
                    status = None
                elif hasattr(e, 'code'):
                    reason = None
                    status = e.code
            except Exception, e:
                LOG.warning('Unexpected error: %s', e)
                continue
            else:
                status = response.getcode()
                body = response.read()

            rtt = int((time.time() - start) * 1000)  # round-trip time

            try:
                description = HTTP_RESPONSES[status]
            except KeyError:
                description = 'undefined'

            if not status:
                event = 'HttpConnectionError'
                severity = severity_code.MAJOR
                value = reason
                text = 'Error during connection or data transfer (timeout=%d).' % CONF.urlmon_max_timeout

            elif status_regex:
                if re.search(status_regex, str(status)):
                    event = 'HttpResponseRegexOK'
                    severity = severity_code.NORMAL
                    value = '%s (%d)' % (description, status)
                    text = 'HTTP server responded with status code %d that matched "%s" in %dms' % (status, status_regex, rtt)
                else:
                    event = 'HttpResponseRegexError'
                    severity = severity_code.MAJOR
                    value = '%s (%d)' % (description, status)
                    text = 'HTTP server responded with status code %d that failed to match "%s"' % (status, status_regex)

            elif 100 <= status <= 199:
                event = 'HttpInformational'
                severity = severity_code.NORMAL
                value = '%s (%d)' % (description, status)
                text = 'HTTP server responded with status code %d in %dms' % (status, rtt)

            elif 200 <= status <= 299:
                event = 'HttpResponseOK'
                severity = severity_code.NORMAL
                value = '%s (%d)' % (description, status)
                text = 'HTTP server responded with status code %d in %dms' % (status, rtt)

            elif 300 <= status <= 399:
                event = 'HttpRedirection'
                severity = severity_code.MINOR
                value = '%s (%d)' % (description, status)
                text = 'HTTP server responded with status code %d in %dms' % (status, rtt)

            elif 400 <= status <= 499:
                event = 'HttpClientError'
                severity = severity_code.MINOR
                value = '%s (%d)' % (description, status)
                text = 'HTTP server responded with status code %d in %dms' % (status, rtt)

            elif 500 <= status <= 599:
                event = 'HttpServerError'
                severity = severity_code.MAJOR
                value = '%s (%d)' % (description, status)
                text = 'HTTP server responded with status code %d in %dms' % (status, rtt)

            else:
                event = 'HttpUnknownError'
                severity = severity_code.WARNING
                value = 'UNKNOWN'
                text = 'HTTP request resulted in an unhandled error.'

            if event in ['HttpResponseOK', 'HttpResponseRegexOK']:
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

            LOG.debug("URL: %s, Status: %s (%s), Round-Trip Time: %dms -> %s",
                      check['url'], description, status, rtt, event)

            # Forward metric data to Graphite
            if status and status <= 299:
                avail = 100.0   # 1xx, 2xx -> 100% available
            else:
                avail = 0.0

            self.carbon.metric_send('alert.urlmon.%s.availability' % check['resource'], '%.1f' % avail)  # %
            self.carbon.metric_send('alert.urlmon.%s.responseTime' % check['resource'], '%d' % rtt)  # ms

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
                attributes={
                    'thresholdInfo': threshold_info
                }
            )

            suppress = Transformers.normalise_alert(urlmonAlert)
            if suppress:
                LOG.info('Suppressing %s alert', urlmonAlert.event)
                LOG.debug('%s', urlmonAlert)

            elif self.dedup.is_send(urlmonAlert):
                try:
                    self.api.send(urlmonAlert)
                except Exception, e:
                    LOG.warning('Failed to send alert: %s', e)

            self.queue.task_done()
            LOG.info('%s check complete.', self.getName())

        self.queue.task_done()


class UrlmonDaemon(Daemon):

    urlmon_opts = {
        'urlmon_file': '/etc/alerta/alert-urlmon.targets',
        'urlmon_max_timeout': 15,  # seconds
        'urlmon_slow_warning': 2000,   # ms
        'urlmon_slow_critical': 5000,  # ms
    }

    def __init__(self, prog, **kwargs):

        config.register_opts(UrlmonDaemon.urlmon_opts)

        Daemon.__init__(self, prog, kwargs)

    def run(self):

        self.running = True

        # Create internal queue
        self.queue = Queue.Queue()

        self.api = ApiClient()

        self.dedup = DeDup()

        self.carbon = Carbon()  # graphite metrics

        # Initialiase alert rules
        urls = init_urls()

        # Start worker threads
        LOG.debug('Starting %s worker threads...', CONF.server_threads)
        for i in range(CONF.server_threads):
            w = WorkerThread(self.api, self.queue, self.dedup, self.carbon)
            try:
                w.start()
            except Exception, e:
                LOG.error('Worker thread #%s did not start: %s', i, e)
                continue
            LOG.info('Started worker thread: %s', w.getName())

        while not self.shuttingdown:
            try:
                for url in urls:
                    self.queue.put((url, time.time()))

                LOG.debug('Send heartbeat...')
                heartbeat = Heartbeat(tags=[__version__])
                try:
                    self.api.send(heartbeat)
                except Exception, e:
                    LOG.warning('Failed to send heartbeat: %s', e)

                time.sleep(CONF.loop_every)
                LOG.info('URL check queue length is %d', self.queue.qsize())
                self.carbon.metric_send('alert.urlmon.queueLength', self.queue.qsize())

            except (KeyboardInterrupt, SystemExit):
                self.shuttingdown = True

        LOG.info('Shutdown request received...')
        self.running = False

        for i in range(CONF.server_threads):
            self.queue.put(None)
        w.join()
