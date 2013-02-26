
import sys
import time
import datetime
import yaml
import threading
import Queue
import json

import pytz

from alerta.common import config
from alerta.common import log as logging
from alerta.common.daemon import Daemon
from alerta.alert import Alert
from alerta.common.mq import Messaging
from alerta.common.mongo import Database

LOG = logging.getLogger(__name__)
CONF = config.CONF

#TODO(nsatterl): add this to default system config

LOGFILE = '/var/log/alerta/alerta.log'
PIDFILE = '/var/run/alerta/alerta.pid'
ALERTCONF = '/opt/alerta/alerta/alerta.yaml'

_SELECT_TIMEOUT = 30

__program__ = 'alerta'
__version__ = '1.6.1'


class WorkerThread(threading.Thread):

    def __init__(self, mq, queue):

        threading.Thread.__init__(self)
        LOG.debug('Initialising %s...', self.getName())

        self.input_queue = queue
        self.mq = mq

        self.db = Database()

    def run(self):

        # TODO(nsatterl): for DEBUG only
        #import pdb; pdb.set_trace()

        while True:

            LOG.debug('Waiting on alert input queue')
            alert = self.input_queue.get()
            if not alert:
                LOG.info('%s is shutting down.', self.getName())
                break

            # TODO(nsatterl): the following should be helper utilities

            # Convert createTime
            createTime = datetime.datetime.strptime(alert['createTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
            createTime = createTime.replace(tzinfo=pytz.utc)

            # Convert receiveTime
            receiveTime = datetime.datetime.strptime(alert['receiveTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
            receiveTime = receiveTime.replace(tzinfo=pytz.utc)

            # Handle heartbeats
            if alert['type'] == 'heartbeat':
                LOG.debug('update heartbeat')
                #self.hb.update_hb(alert)      # TODO(nsatterl): rename alert to payload or data or something

                try:
                    self.db.update(
                        {"origin": alert['origin']},
                        {"origin": alert['origin'], "version": alert['version'], "createTime": createTime, "receiveTime": receiveTime},
                        True)
                except Exception, e:
                    LOG.error('Update failed: %s', e)
                    sys.exit(1)
                LOG.info('%s : heartbeat from %s', alert['id'], alert['origin'])
                return

            start = time.time()
            alertid = alert['id']
            LOG.info('%s : %s', alertid, alert['summary'])

            # Load alert transforms
            try:
                alertconf = yaml.load(open(ALERTCONF))
                LOG.info('Loaded %d alert transforms and blackout rules OK', len(alertconf))
            except Exception, e:
                alertconf = dict()
                LOG.warning('Failed to load alert transforms and blackout rules: %s', e)

            # Apply alert transforms and blackouts
            suppress = False
            for conf in alertconf:
                LOG.debug('alertconf: %s', conf)
                if all(item in alert.items() for item in conf['match'].items()):
                    if 'parser' in conf:
                        LOG.debug('Loading parser %s', conf['parser'])
                        try:
                            exec(open('%s/%s.py' % (CONF.parser_dir, conf['parser']))) in globals(), locals()
                            LOG.info('Parser %s/%s exec OK', CONF.parser_dir, conf['parser'])
                        except Exception, e:
                            LOG.warning('Parser %s failed: %s', conf['parser'], e)
                    if 'event' in conf:
                        event = conf['event']
                    if 'resource' in conf:
                        resource = conf['resource']
                    if 'severity' in conf:
                        severity = conf['severity']
                    if 'group' in conf:
                        group = conf['group']
                    if 'value' in conf:
                        value = conf['value']
                    if 'text' in conf:
                        text = conf['text']
                    if 'environment' in conf:
                        environment = [conf['environment']]
                    if 'service' in conf:
                        service = [conf['service']]
                    if 'tags' in conf:
                        tags = conf['tags']
                    if 'correlatedEvents' in conf:
                        correlate = conf['correlatedEvents']
                    if 'thresholdInfo' in conf:
                        threshold = conf['thresholdInfo']
                    if 'suppress' in conf:
                        suppress = conf['suppress']
                    break

            if suppress:
                LOG.info('%s : Suppressing alert %s', alert['id'], alert['summary'])
                return

            createTime = datetime.datetime.strptime(alert['createTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
            createTime = createTime.replace(tzinfo=pytz.utc)

            receiveTime = datetime.datetime.strptime(alert['receiveTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
            receiveTime = receiveTime.replace(tzinfo=pytz.utc)

            # Add expire timestamp
            if 'timeout' in alert and alert['timeout'] == 0:
                expireTime = ''
            elif 'timeout' in alert and alert['timeout'] > 0:
                expireTime = createTime + datetime.timedelta(seconds=alert['timeout'])
            else:
                alert['timeout'] = CONF.alert_timeout
                expireTime = createTime + datetime.timedelta(seconds=alert['timeout'])

            if self.db.is_duplicate(alert['environment'], alert['resource'], alert['event'], alert['severity']):
                previous_severity = self.db.get_severity( alert['environment'], alert['resource'], alert['event'])
                LOG.info('%s : Duplicate alert -> update dup count', alertid)
                # Duplicate alert .. 1. update existing document with lastReceiveTime, lastReceiveId, text, summary, value, tags and origin
                #                    2. increment duplicate count

                #self.db.alerts.modify_alert()

                update = {
                    "lastReceiveTime": receiveTime,
                    "expireTime": expireTime,
                    "lastReceiveId": alertid,
                    "text": alert['text'],
                    "summary": alert['summary'],
                    "value": alert['value'],
                    "tags": alert['tags'],
                    "repeat": True,
                    "origin": alert['origin'],
                    "trendIndication": 'noChange',
                }

                # TODO(nsatterl): for DEBUG only
                #import pdb; pdb.set_trace()
                enrichedAlert = self.db.duplicate_alert(alert['environment'], alert['resource'], alert['event'], **update)

                print alert
                if alert['status'] not in ['OPEN', 'ACK', 'CLOSED']:
                    if alert['severity'] != 'NORMAL':
                        status = 'OPEN'
                    else:
                        status = 'CLOSED'
                else:
                    status = 'UNKNOWN'

                status = calculate_status(alert['severity'], previous_severity)
                if status:
                    self.db.update_status(alert['environment'], alert['resource'], alert['event'], status)

                self.input_queue.task_done()

            elif self.db.is_correlated(alert['environment'], alert['resource'], alert['event']):
                previous_severity = self.db.get_severity( alert['environment'], alert['resource'], alert['event'])
                LOG.info('%s : Event and/or severity change %s %s -> %s update details', alertid, alert['event'], previous_severity, alert['severity'])

                # Diff sev alert ... 1. update existing document with severity, createTime, receiveTime, lastReceiveTime, previousSeverity,
                #                        severityCode, lastReceiveId, text, summary, value, tags and origin
                #                    2. set duplicate count to zero
                #                    3. push history

                # TODO(nsatterl): determine ti based on current and previous severity
                trend_indication = 'moreSevere' or 'lessSevere'

                update = {
                    "event": alert['event'],
                    "severity": alert['severity'],
                    "severityCode": alert['severityCode'],
                    "createTime": createTime,
                    "receiveTime": receiveTime,
                    "lastReceiveTime": receiveTime,
                    "expireTime": expireTime,
                    "previousSeverity": previous_severity,
                    "lastReceiveId": alertid,
                    "text": alert['text'],
                    "summary": alert['summary'],
                    "value": alert['value'],
                    "tags": alert['tags'],
                    "repeat": False,
                    "origin": alert['origin'],
                    "thresholdInfo": alert['thresholdInfo'],
                    "trendIndication": trend_indication,
                    "duplicateCount": 0
                }
                enrichedAlert = self.db.modify_alert(alert['environment'], alert['resource'], alert['event'], **update)

                status = calculate_status(alert['severity'], previous_severity)
                if status:
                    self.db.update_status(alert['environment'], alert['resource'], alert['event'], status)

                # Forward alert to notify topic and logger queue
                self.mq.send(enrichedAlert, CONF.outbound_queue)
                self.mq.send(enrichedAlert, CONF.outbound_topic)

                self.input_queue.task_done()
                LOG.info('%s : Alert forwarded to %s and %s', alert['id'], CONF.outbound_queue, CONF.outbound_topic)

            else:
                LOG.info('%s : New alert -> insert', alertid)
                # New alert so ... 1. insert entire document
                #                  2. push history
                #                  3. set duplicate count to zero

                trend_indication = 'noChange'

                newAlert = Alert(
                    alertid=alertid,
                    resource=alert['resource'],
                    event=alert['event'],
                    correlate=alert['correlatedEvents'],
                    group=alert['group'],
                    value=alert['value'],
                    severity=alert['severity'],
                    environment=alert['environment'],
                    service=alert['service'],
                    text=alert['text'],
                    event_type=alert['type'],
                    tags=alert['tags'],
                    origin=alert['origin'],
                    threshold_info=alert['thresholdInfo'],
                    summary=alert['summary'],
                    timeout=alert['timeout'],
                    create_time=alert['createTime'],
                    receive_time=alert['receiveTime'],
                    last_receive_time=alert['receiveTime'],
                    duplicate_count=0,
                    status="OPEN",  # TODO(nsatterl): status.OPEN
                    trend_indication=trend_indication,
                    last_receive_id=alertid,
                )
                self.db.save_alert(newAlert)

                # if alert['severity'] != 'NORMAL':
                #     status = 'OPEN'
                # else:
                #     status = 'CLOSED'
                #
                status = 'OPEN' if alert['severity'] != 'NORMAL' else 'CLOSED'
                LOG.debug('severity = %s => status = %s', alert['severity'], status)
                self.db.update_status(alert['environment'], alert['resource'], alert['event'], status)

                # Forward alert to notify topic and logger queue
                self.mq.send(enrichedAlert, CONF.outbound_queue)
                self.mq.send(enrichedAlert, CONF.outbound_topic)

                self.input_queue.task_done()
                LOG.info('%s : Alert forwarded to %s and %s', alert['id'], CONF.outbound_queue, CONF.outbound_topic)

            # # Update management stats
            # proc_latency = int((time.time() - start) * 1000)
            # self.mgmt.update(
            #     { "group": "alerts", "name": "processed", "type": "timer", "title": "Alert process rate and duration", "description": "Time taken to process the alert" },
            #     { '$inc': { "count": 1, "totalTime": proc_latency}},
            #     True)
            # delta = receiveTime - createTime
            # recv_latency = int(delta.days * 24 * 60 * 60 * 1000 + delta.seconds * 1000 + delta.microseconds / 1000)
            # self.mgmt.update(
            #     { "group": "alerts", "name": "received", "type": "timer", "title": "Alert receive rate and latency", "description": "Time taken for alert to be received by the server" },
            #     { '$inc': { "count": 1, "totalTime": recv_latency}},
            #     True)
            # queue_len = queue.qsize()
            # self.mgmt.update(
            #     { "group": "alerts", "name": "queue", "type": "gauge", "title": "Alert internal queue length", "description": "Length of internal alert queue" },
            #     { '$set': { "value": queue_len }},
            #     True)
            # LOG.info('%s : Alert receive latency = %s ms, process latency = %s ms, queue length = %s', alertid, recv_latency, proc_latency, queue_len)
            #
            # heartbeatTime = datetime.datetime.utcnow()
            # heartbeatTime = heartbeatTime.replace(tzinfo=pytz.utc)
            # self.hb.update(
            #     { "origin": "%s/%s" % (__program__, os.uname()[1]) },
            #     { "origin": "%s/%s" % (__program__, os.uname()[1]), "version": __version__, "createTime": heartbeatTime, "receiveTime": heartbeatTime },
            #     True)

        self.input_queue.task_done()


def calculate_status(severity, previous_severity):

    status = None
    if severity in ['DEBUG', 'INFORM']:
        status = 'OPEN'
    elif severity == 'NORMAL':
        status = 'CLOSED'
    elif severity == 'WARNING':
        if previous_severity in ['NORMAL']:
            status = 'OPEN'
    elif severity == 'MINOR':
        if previous_severity in ['NORMAL', 'WARNING']:
            status = 'OPEN'
    elif severity == 'MAJOR':
        if previous_severity in ['NORMAL', 'WARNING', 'MINOR']:
            status = 'OPEN'
    elif severity == 'CRITICAL':
        if previous_severity in ['NORMAL', 'WARNING', 'MINOR', 'MAJOR']:
            status = 'OPEN'
    else:
        status = 'UNKNOWN'

    return status


class MessageHandler(object):

    def __init__(self, queue):
        self.queue = queue

    def on_connecting(self, host_and_port):
        LOG.info('Connecting to %s', host_and_port)

    def on_connected(self, headers, body):
        LOG.info('Connected to %s %s', headers, body)

    def on_disconnected(self):
        # TODO(nsatterl): auto-reconnect
        LOG.error('Connection to messaging server has been lost.')

    def on_message(self, headers, body):

        LOG.info("Received %s %s", headers['type'], headers['correlation-id'])
        LOG.debug("Received body : %s", json.dumps(body, indent=4))

        # TODO(nsatterl): Use validate_alert() function
        try:
            alert = json.loads(body)
        except ValueError, e:
            LOG.error("Could not decode JSON message - %s", e)
            return

        # Set receiveTime
        receiveTime = datetime.datetime.utcnow()
        alert['receiveTime'] = receiveTime.replace(microsecond=0).isoformat() + ".%03dZ" % (receiveTime.microsecond // 1000)

        LOG.debug('Queueing alert %s', alert)

        # Queue alert for processing
        self.queue.put(alert)

    def on_receipt(self, headers, body):
        LOG.debug('Receipt received %s %s', headers, body)

    def on_error(self, headers, body):
        LOG.error('Send failed %s %s', headers, body)

    def on_send(self, headers, body):
        LOG.debug('Sending message %s %s', headers, body)


class AlertaDaemon(Daemon):

    def run(self):
        self.running = True

        # Create internal queue
        self.queue = Queue.Queue()

        # Connect to message queue
        self.mq = Messaging()
        self.mq.connect(callback=MessageHandler(self.queue))
        self.mq.subscribe()

        # Start worker threads
        LOG.debug('Starting %s alert handler threads...', CONF.server_threads)
        for i in range(CONF.server_threads):
            w = WorkerThread(self.mq, self.queue)
            try:
                w.start()
            except Exception, e:
                LOG.error('Worker thread #%s did not start: %s', i, e)

            LOG.info('Started alert handler thread: %s', w.getName())

        while not self.shuttingdown:
            try:
                time.sleep(0.1)
            except (KeyboardInterrupt, SystemExit):
                self.shuttingdown = True
                for i in range(CONF.server_threads):
                    self.queue.put(None)

        LOG.info('Shutdown request received...')
        self.running = False

        LOG.info('Disconnecting from message broker...')
        self.mq.disconnect()