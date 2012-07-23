#!/usr/bin/env python
########################################
#
# alerta.py - Alert Server Module
#
########################################

import os
import sys
import time
try:
    import json
except ImportError:
    import simplejson as json
import stomp
import pymongo
import datetime
import pytz
import logging
import re

__program__ = 'alerta'
__version__ = '1.4.5'

BROKER_LIST  = [('localhost', 61613)] # list of brokers for failover
ALERT_QUEUE  = '/queue/alerts' # inbound
NOTIFY_TOPIC = '/topic/notify' # outbound
LOGGER_QUEUE = '/queue/logger' # outbound

DEFAULT_TIMEOUT = 86400 # expire OPEN alerts after 1 day
EXPIRATION_TIME = 600 # seconds = 10 minutes

LOGFILE = '/var/log/alerta/alerta.log'
PIDFILE = '/var/run/alerta/alerta.pid'

# Global variables
conn = None
alerts = None
mgmt = None

# Extend JSON Encoder to support ISO 8601 format dates
class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.replace(microsecond=0).isoformat() + ".%03dZ" % (obj.microsecond//1000)
        else:
            return json.JSONEncoder.default(self, obj)

class MessageHandler(object):

    def on_error(self, headers, body):
        logging.error('Received an error %s', body)

    def on_message(self, headers, body):
        global alerts, mgmt, hb, conn

        start = time.time()
        logging.debug("Received alert : %s", body)

        alert = dict()
        try:
            alert = json.loads(body)
        except ValueError, e:
            logging.error("Could not decode JSON - %s", e)
            return

        # Move 'id' to '_id' ...
        alertid = alert['id']
        alert['_id'] = alertid
        del alert['id']

        # Add receive timestamp
        receiveTime = datetime.datetime.utcnow()
        receiveTime = receiveTime.replace(tzinfo=pytz.utc)

        createTime = datetime.datetime.strptime(alert['createTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
        createTime = createTime.replace(tzinfo=pytz.utc)

        # Handle heartbeats
        if alert['type'] == 'heartbeatAlert':
            hb.update(
                { "origin": alert['origin'] },
                { "origin": alert['origin'], "version": alert['version'], "createTime": createTime, "receiveTime": receiveTime },
                True)
            logging.info('%s : heartbeat from %s', alertid, alert['origin'])
            return

        logging.info('%s : %s', alertid, alert['summary'])

        # Add expire timestamp
        if 'timeout' in alert and alert['timeout'] == 0:
            expireTime = ''
        elif 'timeout' in alert and alert['timeout'] > 0:
            expireTime = createTime + datetime.timedelta(seconds=alert['timeout'])
        else:
            alert['timeout'] = DEFAULT_TIMEOUT
            expireTime = createTime + datetime.timedelta(seconds=alert['timeout'])

        if alerts.find_one({"resource": alert['resource'], "event": alert['event'], "severity": alert['severity']}):
            logging.info('%s : Duplicate alert -> update dup count', alertid)
            # Duplicate alert .. 1. update existing document with lastReceiveTime, lastReceiveId, text, summary, value, tags and origin
            #                    2. increment duplicate count
            alerts.update(
                { "resource": alert['resource'], "event": alert['event']},
                { '$set': { "lastReceiveTime": receiveTime, "expireTime": expireTime,
                            "lastReceiveId": alertid, "text": alert['text'], "summary": alert['summary'], "value": alert['value'],
                            "tags": alert['tags'], "repeat": True, "origin": alert['origin'] },
                  '$inc': { "duplicateCount": 1 }})

            if alerts.find_one({"resource": alert['resource'], "event": alert['event']}, {"status": 1, "_id": 0})['status'] not in ['OPEN','ACK','CLOSED']:
                if alert['severity'] != 'NORMAL':
                    status = 'OPEN'
                else:
                    status = 'CLOSED'
            else:
                status = None

            if status:
                updateTime = datetime.datetime.utcnow()
                updateTime = updateTime.replace(tzinfo=pytz.utc)
                alerts.update(
                    { "resource": alert['resource'], '$or': [{"event": alert['event']}, {"correlatedEvents": alert['event']}]},
                    { '$set': { "status": status },
                      '$push': { "history": { "status": status, "updateTime": updateTime } }})
                logging.info('%s : Alert status for duplicate %s %s alert changed to %s', alertid, alert['severity'], alert['event'], status)
            else:
                logging.info('%s : Alert status for duplicate %s %s alert unchanged because either OPEN, ACK or CLOSED', alertid, alert['severity'], alert['event'])

            # Forward alert to notify topic and logger queue
            alert = alerts.find_one({"lastReceiveId": alertid}, {"history": 0})

            headers['type']           = alert['type']
            headers['correlation-id'] = alertid
            headers['persistent']     = 'true'
            headers['expires']        = int(time.time() * 1000) + EXPIRATION_TIME * 1000
            headers['repeat']         = 'true'

            alert['id'] = alert['_id']
            del alert['_id']

            logging.info('%s : Fwd alert to %s', alertid, NOTIFY_TOPIC)
            conn.send(json.dumps(alert, cls=DateEncoder), headers, destination=NOTIFY_TOPIC)
            logging.info('%s : Fwd alert to %s', alertid, LOGGER_QUEUE)
            conn.send(json.dumps(alert, cls=DateEncoder), headers, destination=LOGGER_QUEUE)

        elif alerts.find_one({"resource": alert['resource'], '$or': [{"event": alert['event']}, {"correlatedEvents": alert['event']}]}):
            previousSeverity = alerts.find_one({"resource": alert['resource'], '$or': [{"event": alert['event']}, {"correlatedEvents": alert['event']}]}, { "severity": 1 , "_id": 0})['severity']
            logging.info('%s : Event and/or severity change %s %s -> %s update details', alertid, alert['event'], previousSeverity, alert['severity'])
            # Diff sev alert ... 1. update existing document with severity, createTime, receiveTime, lastReceiveTime, previousSeverity,
            #                        severityCode, lastReceiveId, text, summary, value, tags and origin
            #                    2. set duplicate count to zero
            #                    3. push history

            alerts.update(
                { "resource": alert['resource'], '$or': [{"event": alert['event']}, {"correlatedEvents": alert['event']}]},
                { '$set': { "event": alert['event'], "severity": alert['severity'], "severityCode": alert['severityCode'],
                            "createTime": createTime, "receiveTime": receiveTime, "lastReceiveTime": receiveTime, "expireTime": expireTime,
                            "previousSeverity": previousSeverity, "lastReceiveId": alertid, "text": alert['text'], "summary": alert['summary'], "value": alert['value'],
                            "tags": alert['tags'], "repeat": False, "origin": alert['origin'], "thresholdInfo": alert['thresholdInfo'], "duplicateCount": 0 },
                  '$push': { "history": { "createTime": createTime, "receiveTime": receiveTime, "severity": alert['severity'], "event": alert['event'],
                             "severityCode": alert['severityCode'], "value": alert['value'], "text": alert['text'], "id": alertid }}})

            # Update alert status
            status = None
            if alert['severity'] == 'NORMAL':
                status = 'CLOSED'
            elif alert['severity'] == 'WARNING':
                if previousSeverity in ['NORMAL']:
                    status = 'OPEN'
            elif alert['severity'] == 'MINOR':
                if previousSeverity in ['NORMAL','WARNING']:
                    status = 'OPEN'
            elif alert['severity'] == 'MAJOR':
                if previousSeverity in ['NORMAL','WARNING','MINOR']:
                    status = 'OPEN'
            elif alert['severity'] == 'CRITICAL':
                if previousSeverity in ['NORMAL','WARNING','MINOR','MAJOR']:
                    status = 'OPEN'

            if status:
                updateTime = datetime.datetime.utcnow()
                updateTime = updateTime.replace(tzinfo=pytz.utc)
                alerts.update(
                    { "resource": alert['resource'], '$or': [{"event": alert['event']}, {"correlatedEvents": alert['event']}]},
                    { '$set': { "status": status },
                      '$push': { "history": { "status": status, "updateTime": updateTime } }})
                logging.info('%s : Alert status for %s %s alert with diff event/severity changed to %s', alertid, alert['severity'], alert['event'], status)

            # Forward alert to notify topic and logger queue
            alert = alerts.find_one({"lastReceiveId": alertid}, {"history": 0})

            headers['type']           = alert['type']
            headers['correlation-id'] = alertid
            headers['persistent']     = 'true'
            headers['expires']        = int(time.time() * 1000) + EXPIRATION_TIME * 1000
            headers['repeat']         = 'false'

            alert['id'] = alert['_id']
            del alert['_id']

            logging.info('%s : Fwd alert to %s', alertid, NOTIFY_TOPIC)
            conn.send(json.dumps(alert, cls=DateEncoder), headers, destination=NOTIFY_TOPIC)
            logging.info('%s : Fwd alert to %s', alertid, LOGGER_QUEUE)
            conn.send(json.dumps(alert, cls=DateEncoder), headers, destination=LOGGER_QUEUE)

        else:
            logging.info('%s : New alert -> insert', alertid)
            # New alert so ... 1. insert entire document
            #                  2. push history
            #                  3. set duplicate count to zero

            alert['lastReceiveId']    = alertid
            alert['createTime']       = createTime
            alert['receiveTime']      = receiveTime
            alert['lastReceiveTime']  = receiveTime
            alert['expireTime']       = expireTime
            alert['previousSeverity'] = 'UNKNOWN'
            alert['repeat']           = False
            if alert['severity'] != 'NORMAL':
                status = 'OPEN'
            else:
                status = 'CLOSED'
            alert['status'] = status

            alerts.insert(alert)
            alerts.update(
                { "resource": alert['resource'], "event": alert['event'] },
                { '$push': { "history": { "createTime": createTime, "receiveTime": receiveTime, "severity": alert['severity'], "event": alert['event'],
                             "severityCode": alert['severityCode'], "value": alert['value'], "text": alert['text'], "id": alertid }},
                  '$set': { "duplicateCount": 0 }})

            updateTime = datetime.datetime.utcnow()
            updateTime = updateTime.replace(tzinfo=pytz.utc)
            alerts.update(
                { "resource": alert['resource'], "event": alert['event'] },
                { '$set': { "status": status },
                  '$push': { "history": { "status": status, "updateTime": updateTime } }})
            logging.info('%s : Alert status for new %s %s alert set to %s', alertid, alert['severity'], alert['event'], status)

            # Forward alert to notify topic and logger queue
            alert = alerts.find_one({"_id": alertid}, {"_id": 0, "history": 0})

            headers['type']           = alert['type']
            headers['correlation-id'] = alertid
            headers['persistent']     = 'true'
            headers['expires']        = int(time.time() * 1000) + EXPIRATION_TIME * 1000
            headers['repeat']         = 'false'

            alert['id'] = alertid

            logging.info('%s : Fwd alert to %s', alertid, NOTIFY_TOPIC)
            conn.send(json.dumps(alert, cls=DateEncoder), headers, destination=NOTIFY_TOPIC)
            logging.info('%s : Fwd alert to %s', alertid, LOGGER_QUEUE)
            conn.send(json.dumps(alert, cls=DateEncoder), headers, destination=LOGGER_QUEUE)

        diff = int((time.time() - start) * 1000)
        mgmt.update(
            { "group": "alerts", "name": "processed", "type": "timer", "title": "Alert process rate and duration", "description": "Time taken to process the alert" },
            { '$inc': { "count": 1, "totalTime": diff}},
           True)
        delta = receiveTime - createTime
        diff = int(delta.days * 24 * 60 * 60 * 1000 + delta.seconds * 1000 + delta.microseconds / 1000)
        mgmt.update(
            { "group": "alerts", "name": "received", "type": "timer", "title": "Alert receive rate and latency", "description": "Time taken for alert to be received by the server" },
            { '$inc': { "count": 1, "totalTime": diff}},
           True)

        heartbeatTime = datetime.datetime.utcnow()
        heartbeatTime = heartbeatTime.replace(tzinfo=pytz.utc)
        hb.update(
            { "origin": "%s/%s" % (__program__, os.uname()[1]) },
            { "origin": "%s/%s" % (__program__, os.uname()[1]), "version": __version__, "createTime": heartbeatTime, "receiveTime": heartbeatTime },
            True)

    def on_disconnected(self):
        global conn

        logging.warning('Connection lost. Attempting auto-reconnect to %s', ALERT_QUEUE)
        conn.start()
        conn.connect(wait=True)
        conn.subscribe(destination=ALERT_QUEUE, ack='auto')

def main():
    global alerts, mgmt, hb, conn

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s alerta[%(process)d] %(levelname)s - %(message)s", filename=LOGFILE)
    logging.info('Starting up Alerta version %s', __version__)

    # Write pid file
    if os.path.isfile(PIDFILE):
        logging.error('%s already exists, exiting', PIDFILE)
        sys.exit(1)
    else:
        file(PIDFILE, 'w').write(str(os.getpid()))
   
    # Connection to MongoDB
    try:
        mongo = pymongo.Connection()
        db = mongo.monitoring
        alerts = db.alerts
        mgmt = db.status
        hb = db.heartbeats
    except pymongo.errors.ConnectionFailure, e:
        logging.error('Mongo connection failure: %s', e)
        sys.exit(1)

    # Connect to message broker
    try:
        conn = stomp.Connection(BROKER_LIST)
        conn.set_listener('', MessageHandler())
        conn.start()
        conn.connect(wait=True)
        conn.subscribe(destination=ALERT_QUEUE, ack='auto')
    except Exception, e:
        logging.error('Stomp connection error: %s', e)

    while True:
        try:
            time.sleep(0.01)
        except (KeyboardInterrupt, SystemExit):
            conn.disconnect()
            os.unlink(PIDFILE)
            sys.exit(0)

if __name__ == '__main__':
    main()
