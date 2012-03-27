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

__version__ = "1.0"

BROKER_LIST  = [('devmonsvr01',61613), ('localhost', 61613)] # list of brokers for failover
ALERT_QUEUE  = '/queue/alerts' # inbound
NOTIFY_TOPIC = '/topic/notify' # outbound

LOGFILE = '/var/log/alerta/alerta.log'
PIDFILE = '/var/run/alerta/alerta.pid'

# Extend JSON Encoder to support ISO 8601 format dates
class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        else:
            return json.JSONEncoder.default(self, obj)

class MessageHandler(object):
    def on_error(self, headers, body):
        logging.error('Received an error %s', body)

    def on_message(self, headers, body):
        global alerts, mgmt, conn

        start = time.time()
        logging.debug("Received alert; %s", body)

        alert = dict()
        alert = json.loads(body)

        logging.info('%s : %s', alert['uuid'], alert['summary'])

        receiveTime = datetime.datetime.utcnow()
        receiveTime = receiveTime.replace(tzinfo=pytz.utc) # XXX - kludge because python utcnow() is a naive datetime despite the name... bizarre

        m = re.match('(\d+)-(\d+)-(\d+)T(\d+):(\d+):(\d+)\.(\d+)\+00:00', alert['createTime'])
        if m:
            createTime = datetime.datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)), int(m.group(6)), int(m.group(7)), pytz.utc)
        else:
            logging.warning('no datetime match')
            return

        if not alerts.find_one({"source": alert['source'], "event": alert['event']}):
            logging.info('%s New alert %s %s %s', alert['uuid'], alert['source'], alert['event'], alert['severity'])
            # New alert so ... 1. insert entire document
            #                  2. push history
            #                  3. set duplicate count to zero

            alert['receiveTime'] = receiveTime.isoformat()
            alert['lastReceiveTime'] = receiveTime.isoformat()
            alert['repeat'] = False
            alerts.insert(alert)
            alerts.update(
                { "source": alert['source'], "event": alert['event'] },
                { '$push': { "history": { "createTime": createTime.isoformat(), "receiveTime": receiveTime.isoformat(), "severity": alert['severity'], "text": alert['text'], "uuid": alert['uuid'] }}, 
                  '$set': { "duplicateCount": 0 }})

            # Forward alert to notify topic
            logging.info('Fwd alert %s to %s', alert['uuid'], NOTIFY_TOPIC)
            alert = alerts.find_one({"uuid": alert['uuid']}, {"_id": 0, "history": 0})
            expireTime = int(start * 1000) + 5000
            conn.send(json.dumps(alert, cls=DateEncoder), destination=NOTIFY_TOPIC, headers={"persistent": "true", "expires": expireTime, "repeat": "false"}, ack="auto")

        elif alerts.find_one({"source": alert['source'], "event": alert['event'], "severity": alert['severity']}):
            logging.info('%s Duplicate alert %s %s %s', alert['uuid'], alert['source'], alert['event'], alert['severity'])
            # Duplicate alert .. 1. update existing document with lastReceiveTime, uuid, text, summary, value, tags, group and origin
            #                    2. increment duplicate count
            alerts.update(
                { "source": alert['source'], "event": alert['event']},
                { '$set': { "lastReceiveTime": receiveTime.isoformat(),
                            "uuid": alert['uuid'], "text": alert['text'], "summary": alert['summary'], "value": alert['value'],
                            "tags": alert['tags'], "group": alert['group'], "repeat": True, "origin": alert['origin'] },
                  '$inc': { "duplicateCount": 1 }})
            # Forward alert to notify topic
            logging.info('Fwd alert %s to %s', alert['uuid'], NOTIFY_TOPIC)
            alert = alerts.find_one({"uuid": alert['uuid']}, {"_id": 0, "history": 0})
            expireTime = int(start * 1000) + 5000
            conn.send(json.dumps(alert, cls=DateEncoder), destination=NOTIFY_TOPIC, headers={"persistent": "true", "expires": expireTime, "repeat": "true"}, ack="auto")

        else:
            logging.info('%s Diff sev alert %s %s %s', alert['uuid'], alert['source'], alert['event'], alert['severity'])
            previousSeverity = alerts.find_one({"source": alert['source'], "event": alert['event']}, { "severity": 1 , "_id": 0})['severity']
            # Diff sev alert ... 1. update existing document with severity, createTime, receiveTime, lastReceiveTime, (previousSeverity) <-- is this used???
            #                        uuid, text, summary, value, tags, group and origin
            #                    2. set duplicate count to zero
            #                    3. push history
            alerts.update(
                { "source": alert['source'], "event": alert['event']},
                { '$set': { "severity": alert['severity'], "createTime": createTime.isoformat(), "receiveTime": receiveTime.isoformat(), "lastReceiveTime": receiveTime.isoformat(), "previousSeverity": previousSeverity,
                            "uuid": alert['uuid'], "text": alert['text'], "summary": alert['summary'], "value": alert['value'],
                            "tags": alert['tags'], "group": alert['group'], "repeat": False, "origin": alert['origin'],
                            "duplicateCount": 0 },
                  '$push': { "history": { "createTime": createTime.isoformat(), "receiveTime": receiveTime.isoformat(), "severity": alert['severity'], "text": alert['text'], "uuid": alert['uuid'] }}})

            # Forward alert to notify topic
            logging.info('Fwd alert %s to %s', alert['uuid'], NOTIFY_TOPIC)
            alert = alerts.find_one({"uuid": alert['uuid']}, {"_id": 0, "history": 0})
            # conn.send(json.dumps(alert, cls=DateEncoder), destination=NOTIFY_TOPIC, repeat=False)
            expireTime = int(start * 1000) + 5000
            conn.send(json.dumps(alert, cls=DateEncoder), destination=NOTIFY_TOPIC, headers={"persistent": "true", "expires": expireTime, "repeat": "false"}, ack="auto")

        diff = int((time.time() - start) * 1000)
        mgmt.update(
            { "group": "alerts", "name": "received", "type": "counter", "title": "Alerts received", "description": "Alerts received by via the message queue" },
            { '$inc': { "count": 1, "totalTime": diff}},
           True)

    def on_disconnected(self):
        global conn

        logging.warning('Connection lost. Attempting auto-reconnect to %s', ALERT_QUEUE)
        conn.start()
        conn.connect(wait=True)
        conn.subscribe(destination=ALERT_QUEUE, ack='auto')

def main():
    global alerts, mgmt, conn

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s alerta[%(process)d] %(levelname)s - %(message)s", filename=LOGFILE)
    logging.info('Starting up Alerter version %s', __version__)

    # Write pid file
    if os.path.isfile(PIDFILE):
        logging.error('%s already exists, exiting' % PIDFILE)
        sys.exit()
    else:
        file(PIDFILE, 'w').write(str(os.getpid()))
   
    # Connection to MongoDB
    try:
        mongo = pymongo.Connection()
        db = mongo.monitoring
        alerts = db.alerts
        mgmt = db.status
    except Exception, e:
        logging.error('Mongo connection error: %s', e)

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
        except KeyboardInterrupt, SystemExit:
            conn.disconnect()
            os.unlink(PIDFILE)
            sys.exit()

if __name__ == '__main__':
    main()
