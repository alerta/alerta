import sys
import time
import threading
import Queue

import yaml

from alerta.common import config
from alerta.common import log as logging
from alerta.common.daemon import Daemon
from alerta.alert import Alert
from alerta.common.mq import Messaging
from alerta.common.mongo import Database


LOG = logging.getLogger(__name__)
CONF = config.CONF

#TODO(nsatterl): add this to default system config

ALERTCONF = '/opt/alerta/alerta/alerta.yaml'

_SELECT_TIMEOUT = 30

__program__ = 'alerta'
__version__ = '2.0.0'


class WorkerThread(threading.Thread):
    def __init__(self, mq, queue):

        threading.Thread.__init__(self)
        LOG.debug('Initialising %s...', self.getName())

        self.input_queue = queue   # internal queue
        self.mq = mq               # message broker

        self.db = Database()       # mongo database

    def run(self):

        while True:
            LOG.debug('Waiting on input queue...')
            item = self.input_queue.get()

            if not item:
                LOG.info('%s is shutting down.', self.getName())
                break

            # Handle heartbeats
            if item.get_type() == 'Heartbeat':
                LOG.debug('update heartbeat')
                #self.hb.update_hb(alert)      # TODO(nsatterl): rename alert to payload or data or something

                try:
                    self.db.update(
                        {"origin": alert['origin']},
                        {"origin": alert['origin'], "version": alert['version'], "createTime": createTime,
                         "receiveTime": receiveTime},
                        True)
                except Exception, e:
                    LOG.error('Update failed: %s', e)
                    sys.exit(1)
                LOG.info('%s : heartbeat from %s', alert['id'], alert['origin'])
                continue

            alert = item.get_body()
            print alert

            # TODO(nsatterl): fix this!!!!
            #alert = transform(alert)

            if self.db.is_duplicate(alert['environment'], alert['resource'], alert['event'], alert['severity']):

                # Duplicate alert .. 1. update existing document with lastReceiveTime, lastReceiveId, text, summary, value, tags and origin
                #                    2. increment duplicate count

                LOG.info('%s : Duplicate alert -> update dup count', alert['id'])

                update = {
                    "lastReceiveTime": alert['receiveTime'],
                    "expireTime": alert['expireTime'],
                    "lastReceiveId": alert['id'],
                    "text": alert['text'],
                    "summary": alert['summary'],
                    "value": alert['value'],
                    "tags": alert['tags'],
                    "repeat": True,
                    "origin": alert['origin'],
                    "trendIndication": 'noChange',
                }
                self.db.duplicate_alert(alert['environment'], alert['resource'], alert['event'], **update)

                if alert['status'] not in ['OPEN', 'ACK', 'CLOSED']:
                    if alert['severity'] != 'NORMAL':
                        status = 'OPEN'
                    else:
                        status = 'CLOSED'
                else:
                    status = 'UNKNOWN'

                if status:
                    self.db.update_status(alert['environment'], alert['resource'], alert['event'], status)

                self.input_queue.task_done()

            elif self.db.is_correlated(alert['environment'], alert['resource'], alert['event']):

                # Diff sev alert ... 1. update existing document with severity, createTime, receiveTime, lastReceiveTime, previousSeverity,
                #                       severityCode, lastReceiveId, text, summary, value, tags and origin
                #                    2. set duplicate count to zero
                #                    3. push history

                previous_severity = self.db.get_severity(alert['environment'], alert['resource'], alert['event'])
                LOG.info('%s : Event and/or severity change %s %s -> %s update details', alert['id'], alert['event'],
                         previous_severity, alert['severity'])

                # TODO(nsatterl): determine ti based on current and previous severity
                trend_indication = 'moreSevere' or 'lessSevere'

                update = {
                    "event": alert['event'],
                    "severity": alert['severity'],
                    "severityCode": alert['severityCode'],
                    "createTime": alert['createTime'],
                    "receiveTime": alert['receiveTime'],
                    "lastReceiveTime": alert['receiveTime'],
                    "expireTime": alert['expireTime'],
                    "previousSeverity": previous_severity,
                    "lastReceiveId": alert['id'],
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
                LOG.info('%s : New alert -> insert', alert['id'])
                # New alert so ... 1. insert entire document
                #                  2. push history
                #                  3. set duplicate count to zero

                trend_indication = 'noChange'

                newAlert = Alert(
                    alertid=alert['id'],
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
                    status="OPEN", # TODO(nsatterl): status.OPEN
                    trend_indication=trend_indication,
                    last_receive_id=alert['id'],
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
                self.mq.send(newAlert, CONF.outbound_queue)
                self.mq.send(newAlert, CONF.outbound_topic)

                self.input_queue.task_done()
                LOG.info('%s : Alert forwarded to %s and %s', alert['id'], CONF.outbound_queue, CONF.outbound_topic)

        self.input_queue.task_done()


def transform(alert):
    # Load alert transforms
    try:
        alertconf = yaml.load(open(ALERTCONF))
        LOG.info('Loaded %d alert transforms and blackout rules OK', len(alertconf))
    except Exception, e:
        alertconf = dict()
        LOG.warning('Failed to load alert transforms and blackout rules: %s', e)

    suppress = False
    for conf in alertconf:
        LOG.debug('alertconf: %s', conf)
        if all(item in alert.items() for item in conf['match'].items()):
            if 'parser' in conf:
                LOG.debug('Loading parser %s', conf['parser'])
                try:
                    exec (open('%s/%s.py' % (CONF.parser_dir, conf['parser']))) in globals(), locals()
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
        LOG.debug("Received body : %s", body)

        if headers['type'] == 'Heartbeat':
            # TODO(nsatterl): Heartbeat.parse_heartbeat(body) etc.
            pass
        elif headers['type'].endswith('Alert'):
            alert = Alert.parse_alert(body)
            if alert:
                alert.receive_now()
                LOG.debug('Queueing alert %s', alert.get_body())
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
                continue
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