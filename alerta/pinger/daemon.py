
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
from alerta.common.mq import Messaging, MessageHandler
from alerta.common.daemon import Daemon
from alerta.common.dedup import DeDup
from alerta.common.graphite import Carbon

Version = '2.0.9'

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
        targets = yaml.load(open(CONF.yaml_config))
    except Exception, e:
        LOG.error('Failed to load Ping targets: %s', e)
    LOG.info('Loaded %d Ping targets OK', len(targets))

    return targets


class WorkerThread(threading.Thread):

    def __init__(self, mq, queue, dedup, carbon):

        threading.Thread.__init__(self)
        LOG.debug('Initialising %s...', self.getName())

        self.last_event = {}
        self.queue = queue   # internal queue
        self.mq = mq               # message broker
        self.dedup = dedup
        self.carbon = carbon  # graphite metrics

    def run(self):

        while True:
            LOG.debug('Waiting on input queue...')
            item = self.queue.get()

            if not item:
                LOG.info('%s is shutting down.', self.getName())
                break

            environment, service, resource, retries = item

            LOG.info('%s pinging %s', self.getName(), resource)
            if retries > 1:
                rc, rtt, loss, stdout = self.pinger(resource)
            else:
                rc, rtt, loss, stdout = self.pinger(resource, count=5, timeout=CONF.ping_max_timeout)

            if rc != PING_OK and retries:
                LOG.info('Retrying ping %s %s more times', resource, retries)
                self.queue.put((environment, service, resource, retries - 1))
                self.queue.task_done()
                continue

            if rc == PING_OK:
                avg, max = rtt
                self.carbon.metric_send('alert.pinger.%s.avg' % resource, avg)
                self.carbon.metric_send('alert.pinger.%s.max' % resource, max)
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
            elif rc == PING_ERROR:
                event = 'PingError'
                severity = severity_code.WARNING
                text = 'Could not ping node %s.' % resource
                value = stdout
            else:
                LOG.warning('Unknown ping return code: %s', rc)
                continue

            # Defaults
            resource += ':icmp'
            group = 'Network'
            correlate = _PING_ALERTS
            timeout = None
            threshold_info = None
            summary = None
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
                event_type='exceptionAlert',
                tags=None,
                timeout=timeout,
                threshold_info=threshold_info,
                summary=summary,
                raw_data=raw_data,
            )

            if self.dedup.is_send(pingAlert):
                self.mq.send(pingAlert)

            self.queue.task_done()
            LOG.info('%s ping complete.', self.getName())

        self.queue.task_done()

    @staticmethod
    def pinger(node, count=3, interval=1, timeout=5):

        if timeout < count * interval:
            timeout = count * interval + 1
        if timeout > CONF.ping_max_timeout:
            timeout = CONF.ping_max_timeout

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


class PingerMessage(MessageHandler):

    def __init__(self, mq):
        self.mq = mq
        MessageHandler.__init__(self)

    def on_disconnected(self):
        self.mq.reconnect()


class PingerDaemon(Daemon):

    def run(self):

        self.running = True

        # Create internal queue
        self.queue = Queue.Queue()

        # Connect to message queue
        self.mq = Messaging()
        self.mq.connect(callback=PingerMessage(self.mq))

        self.dedup = DeDup()

        self.carbon = Carbon()  # graphite metrics

        # Initialiase ping targets
        ping_list = init_targets()

        # Start worker threads
        LOG.debug('Starting %s worker threads...', CONF.server_threads)
        for i in range(CONF.server_threads):
            w = WorkerThread(self.mq, self.queue, self.dedup, self.carbon)
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
                            self.queue.put((environment, service, target, retries))

                LOG.debug('Send heartbeat...')
                heartbeat = Heartbeat(version=Version)
                self.mq.send(heartbeat)

                LOG.info('Ping queue length is %d', self.queue.qsize())
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
