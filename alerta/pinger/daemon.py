
import sys
import time
import subprocess
import threading
import Queue
import re

import yaml

from alerta.common import log as logging
from alerta.common import config
from alerta.common.alert import Alert
from alerta.common.heartbeat import Heartbeat
from alerta.common import severity_code
from alerta.common.api import ApiClient
from alerta.common.daemon import Daemon
from alerta.common.transform import Transformers
from alerta.common.dedup import DeDup
from alerta.common.graphite import Carbon

__version__ = '3.0.3'

LOG = logging.getLogger(__name__)
CONF = config.CONF


_PING_ALERTS = [
    'PingFailed',
    'PingSlow',
    'PingOK',
    'PingError',
]

PING_OK = 0       # all ping replies received within timeout
PING_FAILED = 1   # some or all ping replies not received or did not respond within timeout
PING_ERROR = 2    # unspecified error with ping


# Initialise Rules
def init_targets():

    targets = list()
    LOG.info('Loading Ping targets...')
    try:
        targets = yaml.load(open(CONF.ping_file))
    except Exception, e:
        LOG.error('Failed to load Ping targets: %s', e)
    LOG.info('Loaded %d Ping targets OK', len(targets))

    return targets


class WorkerThread(threading.Thread):

    def __init__(self, api, queue, dedup, carbon):

        threading.Thread.__init__(self)
        LOG.debug('Initialising %s...', self.getName())

        self.last_event = {}
        self.queue = queue   # internal queue
        self.api = api               # message broker
        self.dedup = dedup
        self.carbon = carbon  # graphite metrics

    def run(self):

        while True:
            LOG.debug('Waiting on input queue...')
            item = self.queue.get()

            if not item:
                LOG.info('%s is shutting down.', self.getName())
                break

            environment, service, resource, retries, queue_time = item

            if time.time() - queue_time > CONF.loop_every:
                LOG.warning('Ping request to %s expired after %d seconds.', resource, int(time.time() - queue_time))
                self.queue.task_done()
                continue

            LOG.info('%s pinging %s...', self.getName(), resource)
            if retries > 1:
                rc, rtt, loss, stdout = self.pinger(resource, count=2, timeout=5)
            else:
                rc, rtt, loss, stdout = self.pinger(resource, count=5, timeout=CONF.ping_max_timeout)

            if rc != PING_OK and retries:
                LOG.info('Retrying ping %s %s more times', resource, retries)
                self.queue.put((environment, service, resource, retries - 1, time.time()))
                self.queue.task_done()
                continue

            if rc == PING_OK:
                avg, max = rtt
                self.carbon.metric_send('alert.pinger.%s.avgRoundTrip' % resource, avg)
                self.carbon.metric_send('alert.pinger.%s.maxRoundTrip' % resource, max)
                self.carbon.metric_send('alert.pinger.%s.availability' % resource, 100.0)
                if avg > CONF.ping_slow_critical:
                    event = 'PingSlow'
                    severity = severity_code.CRITICAL
                    text = 'Node responded to ping in %s ms avg (> %s ms)' % (avg, CONF.ping_slow_critical)
                elif avg > CONF.ping_slow_warning:
                    event = 'PingSlow'
                    severity = severity_code.WARNING
                    text = 'Node responded to ping in %s ms avg (> %s ms)' % (avg, CONF.ping_slow_warning)
                else:
                    event = 'PingOK'
                    severity = severity_code.NORMAL
                    text = 'Node responding to ping avg/max %s/%s ms.' % tuple(rtt)
                value = '%s/%s ms' % tuple(rtt)
            elif rc == PING_FAILED:
                event = 'PingFailed'
                severity = severity_code.MAJOR
                text = 'Node did not respond to ping or timed out within %s seconds' % CONF.ping_max_timeout
                value = '%s%% packet loss' % loss
                self.carbon.metric_send('alert.pinger.%s.availability' % resource, 100.0 - float(loss))
            elif rc == PING_ERROR:
                event = 'PingError'
                severity = severity_code.WARNING
                text = 'Could not ping node %s.' % resource
                value = stdout
                self.carbon.metric_send('alert.pinger.%s.availability' % resource, 0.0)
            else:
                LOG.warning('Unknown ping return code: %s', rc)
                continue

            # Defaults
            resource += ':icmp'
            group = 'Ping'
            correlate = _PING_ALERTS
            timeout = None
            raw_data = stdout

            pingAlert = Alert(
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
                tags=None,
                timeout=timeout,
                raw_data=raw_data,
            )

            suppress = Transformers.normalise_alert(pingAlert)
            if suppress:
                LOG.info('Suppressing %s alert', pingAlert.event)
                LOG.debug('%s', pingAlert)

            elif self.dedup.is_send(pingAlert):
                try:
                    self.api.send(pingAlert)
                except Exception, e:
                    LOG.warning('Failed to send alert: %s', e)

            self.queue.task_done()
            LOG.info('%s ping %s complete.', self.getName(), resource)

        self.queue.task_done()

    @staticmethod
    def pinger(node, count=1, interval=1, timeout=5):

        if timeout <= count * interval:
            timeout = count * interval + 1
        if timeout > CONF.ping_max_timeout:
            timeout = CONF.ping_max_timeout

        if sys.platform == "darwin":
            cmd = "ping -q -c %s -i %s -t %s %s" % (count, interval, timeout, node)
        else:
            cmd = "ping -q -c %s -i %s -w %s %s" % (count, interval, timeout, node)
        ping = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout = ping.communicate()[0].rstrip('\n')
        rc = ping.returncode
        LOG.debug('Ping %s => %s (rc=%d)', cmd, stdout, rc)

        m = re.search('(?P<loss>\d+(\.\d+)?)% packet loss', stdout)
        if m:
            loss = m.group('loss')
        else:
            loss = 'n/a'

        m = re.search('(?P<min>\d+\.\d+)/(?P<avg>\d+\.\d+)/(?P<max>\d+\.\d+)/(?P<mdev>\d+\.\d+)\s+ms', stdout)
        if m:
            rtt = (float(m.group('avg')), float(m.group('max')))
        else:
            rtt = (0, 0)

        if rc == 0:
            LOG.info('%s: is alive %s', node, rtt)
        else:
            LOG.info('%s: not responding', node)

        return rc, rtt, loss, stdout


class PingerDaemon(Daemon):

    pinger_opts = {
        'ping_file': '/etc/alerta/alert-pinger.targets',
        'ping_max_timeout': 15,  # seconds
        'ping_max_retries': 2,
        'ping_slow_warning': 5,    # ms
        'ping_slow_critical': 10,  # ms
        'server_threads': 20,
    }

    def __init__(self, prog, **kwargs):

        config.register_opts(PingerDaemon.pinger_opts)

        Daemon.__init__(self, prog, kwargs)

    def run(self):

        self.running = True

        # Create internal queue
        self.queue = Queue.Queue()

        self.api = ApiClient()

        self.dedup = DeDup()

        self.carbon = Carbon()  # graphite metrics

        # Initialiase ping targets
        ping_list = init_targets()

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
                for p in ping_list:
                    if 'targets' in p and p['targets']:
                        for target in p['targets']:
                            environment = p['environment']
                            service = p['service']
                            retries = p.get('retries', CONF.ping_max_retries)
                            self.queue.put((environment, service, target, retries, time.time()))

                LOG.debug('Send heartbeat...')
                heartbeat = Heartbeat(tags=[__version__])
                try:
                    self.api.send(heartbeat)
                except Exception, e:
                    LOG.warning('Failed to send heartbeat: %s', e)

                time.sleep(CONF.loop_every)
                LOG.info('Ping queue length is %d', self.queue.qsize())
                self.carbon.metric_send('alert.pinger.queueLength', self.queue.qsize())

            except (KeyboardInterrupt, SystemExit):
                self.shuttingdown = True

        LOG.info('Shutdown request received...')
        self.running = False

        for i in range(CONF.server_threads):
            self.queue.put(None)
        w.join()
