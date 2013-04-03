
import time
import threading
import Queue

from alerta.common import config
from alerta.common import log as logging
from alerta.common.daemon import Daemon
from alerta.alert import Alert, Heartbeat, severity, status
from alerta.common.mq import Messaging, MessageHandler
from alerta.server.database import Mongo

Version = '2.0.2'

LOG = logging.getLogger(__name__)
CONF = config.CONF


class WorkerThread(threading.Thread):

    def __init__(self, mq, queue):

        threading.Thread.__init__(self)
        LOG.debug('Initialising %s...', self.getName())

        self.input_queue = queue   # internal queue
        self.mq = mq               # message broker

        self.db = Mongo()       # mongo database

    def run(self):

        while True:
            LOG.debug('Waiting on input queue...')
            try:
                incomingAlert = self.input_queue.get(True, CONF.loop_every)
            except Queue.Empty:
                LOG.debug('Send heartbeat...')
                heartbeat = Heartbeat(version=Version)
                self.mq.send(heartbeat)
                continue

            if not incomingAlert:
                LOG.info('%s is shutting down.', self.getName())
                break

            if incomingAlert.get_type() == 'Heartbeat':
                LOG.info('Heartbeat received...')
                heartbeat = incomingAlert.get_body()
                self.db.update_hb(heartbeat['origin'], heartbeat['version'], heartbeat['createTime'],
                                  heartbeat['receiveTime'])
                self.input_queue.task_done()
                continue
            else:
                LOG.info('Alert received...')

            suppress = incomingAlert.transform_alert()
            if suppress:
                LOG.warning('Suppressing alert %s', incomingAlert.get_id())
                self.input_queue.task_done()
                return

            # Get alert attributes into a dict
            alert = incomingAlert.get_body()

            if self.db.is_duplicate(alert['environment'], alert['resource'], alert['event'], alert['severity']):

                # Duplicate alert .. 1. update existing document with lastReceiveTime, lastReceiveId, text, summary,
                #                       value, tags and origin
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
                    "rawData": alert['rawData'],
                }
                duplicateAlert = self.db.duplicate_alert(environment=alert['environment'], resource=alert['resource'],
                                                         event=alert['event'], update=update)

                if CONF.forward_duplicate:
                    # Forward alert to notify topic and logger queue
                    self.mq.send(duplicateAlert, CONF.outbound_queue)
                    self.mq.send(duplicateAlert, CONF.outbound_topic)

                self.input_queue.task_done()

            elif self.db.is_correlated(alert['environment'], alert['resource'], alert['event']):

                # Diff sev alert ... 1. update existing document with severity, createTime, receiveTime,
                #                       lastReceiveTime, previousSeverity,
                #                       severityCode, lastReceiveId, text, summary, value, tags and origin
                #                    2. set duplicate count to zero
                #                    3. push history

                previous_severity = self.db.get_severity(alert['environment'], alert['resource'], alert['event'])
                LOG.info('%s : Event and/or severity change %s %s -> %s update details', alert['id'], alert['event'],
                         previous_severity, alert['severity'])

                trend_indication = severity.trend(previous_severity, alert['severity'])

                update = {
                    "event": alert['event'],
                    "severity": alert['severity'],
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
                    "rawData": alert['rawData'],
                    "duplicateCount": 0,
                }
                correlatedAlert = self.db.update_alert(environment=alert['environment'], resource=alert['resource'],
                                                       event=alert['event'], update=update)

                new_status = severity.status_from_severity(previous_severity, alert['severity'])
                if new_status:
                    self.db.update_status(environment=alert['environment'], resource=alert['resource'],
                                          event=alert['event'], status=new_status)

                # Forward alert to notify topic and logger queue
                self.mq.send(correlatedAlert, CONF.outbound_queue)
                self.mq.send(correlatedAlert, CONF.outbound_topic)

                self.input_queue.task_done()
                LOG.info('%s : Alert forwarded to %s and %s', alert['id'], CONF.outbound_queue, CONF.outbound_topic)

            else:
                LOG.info('%s : New alert -> insert', alert['id'])
                # New alert so ... 1. insert entire document
                #                  2. push history
                #                  3. set duplicate count to zero

                trend_indication = severity.trend(severity.UNKNOWN, alert['severity'])

                newAlert = Alert(
                    resource=alert['resource'],
                    event=alert['event'],
                    correlate=alert['correlatedEvents'],
                    group=alert['group'],
                    value=alert['value'],
                    status=status.OPEN,
                    severity=alert['severity'],
                    environment=alert['environment'],
                    service=alert['service'],
                    text=alert['text'],
                    event_type=alert['type'],
                    tags=alert['tags'],
                    origin=alert['origin'],
                    repeat=False,
                    duplicate_count=0,
                    threshold_info=alert['thresholdInfo'],
                    summary=alert['summary'],
                    timeout=alert['timeout'],
                    alertid=alert['id'],
                    last_receive_id=alert['id'],
                    create_time=alert['createTime'],
                    receive_time=alert['receiveTime'],
                    last_receive_time=alert['receiveTime'],
                    trend_indication=trend_indication,
                    raw_data=alert['rawData'],
                    more_info=alert['moreInfo'],
                    graph_urls=alert['graphUrls'],
                )
                self.db.save_alert(newAlert)

                new_status = severity.status_from_severity(severity.UNKNOWN, alert['severity'])
                if new_status:
                    self.db.update_status(environment=alert['environment'], resource=alert['resource'],
                                          event=alert['event'], status=new_status)

                # Forward alert to notify topic and logger queue
                self.mq.send(newAlert, CONF.outbound_queue)
                self.mq.send(newAlert, CONF.outbound_topic)

                self.input_queue.task_done()
                LOG.info('%s : Alert forwarded to %s and %s', alert['id'], CONF.outbound_queue, CONF.outbound_topic)

            # update application stats
            self.db.update_metrics(alert['createTime'], alert['receiveTime'])

        self.input_queue.task_done()


class ServerMessage(MessageHandler):

    def __init__(self, mq, queue):

        self.mq = mq
        self.queue = queue

        MessageHandler.__init__(self)

    def on_message(self, headers, body):

        LOG.info("Received %s %s", headers['type'], headers['correlation-id'])
        LOG.debug("Received body : %s", body)

        if headers['type'] == 'Heartbeat':
            heartbeat = Heartbeat.parse_heartbeat(body)
            if heartbeat:
                heartbeat.receive_now()
                LOG.debug('Queueing successfully parsed heartbeat %s', heartbeat.get_body())
                self.queue.put(heartbeat)
        elif headers['type'].endswith('Alert'):
            alert = Alert.parse_alert(body)
            if alert:
                alert.receive_now()
                LOG.debug('Queueing successfully parsed alert %s', alert.get_body())
                self.queue.put(alert)

    def on_disconnected(self):
        self.mq.reconnect()


class AlertaDaemon(Daemon):

    def run(self):

        self.running = True

        # Create internal queue
        self.queue = Queue.Queue()

        # Connect to message queue
        self.mq = Messaging()
        self.mq.connect(callback=ServerMessage(self.mq, self.queue))
        self.mq.subscribe()

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
                LOG.debug('Send heartbeat...')
                heartbeat = Heartbeat(version=Version)
                self.mq.send(heartbeat)

                LOG.debug('Internal queue size is %s messages', self.queue.qsize())

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