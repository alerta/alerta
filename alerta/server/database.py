import sys
import datetime
import pytz

import pymongo

from alerta.common import log as logging
from alerta.common import config
from alerta.common.alert import Alert

LOG = logging.getLogger(__name__)
CONF = config.CONF


class Mongo(object):

    def __init__(self):

        # Connect to MongoDB
        try:
            self.conn = pymongo.MongoClient(CONF.mongo_host, CONF.mongo_port)  # version >= 2.4
        except AttributeError:
            self.conn = pymongo.Connection(CONF.mongo_host, CONF.mongo_port)  # version < 2.4
        except Exception, e:
            LOG.error('MongoDB Client connection error : %s', e)
            sys.exit(1)

        try:
            self.db = self.conn.monitoring  # TODO(nsatterl): make 'monitoring' a SYSTEM DEFAULT
        except Exception, e:
            LOG.error('MongoDB database error : %s', e)
            sys.exit(1)

        LOG.info('Connected to MongoDB server %s:%s', CONF.mongo_host, CONF.mongo_port)
        LOG.debug('MongoDB %s, databases available: %s', self.conn.server_info()['version'], ', '.join(self.conn.database_names()))

        self.create_indexes()

    def create_indexes(self):

        self.db.alerts.create_index([('environment', pymongo.ASCENDING), ('resource', pymongo.ASCENDING),
                                     ('event', pymongo.ASCENDING), ('severity', pymongo.ASCENDING)])
        self.db.alerts.create_index([('_id', pymongo.ASCENDING), ('environment', pymongo.ASCENDING),
                                     ('resource', pymongo.ASCENDING), ('event', pymongo.ASCENDING)])
        self.db.alerts.create_index([('status', pymongo.ASCENDING), ('expireTime', pymongo.ASCENDING)])

    def is_duplicate(self, alert, severity=None):

        if severity:
            found = self.db.alerts.find_one({"environment": alert.environment, "resource": alert.resource, "event": alert.event, "severity": severity})
        else:
            found = self.db.alerts.find_one({"environment": alert.environment, "resource": alert.resource, "event": alert.event})

        return found is not None

    def is_correlated(self, alert):

        found = self.db.alerts.find_one({"environment": alert.environment, "resource": alert.resource,
                                         '$or': [{"event": alert.event}, {"correlatedEvents": alert.event}]})
        return found is not None

    def get_severity(self, alert):

        return self.db.alerts.find_one({"environment": alert.environment, "resource": alert.resource,
                                        '$or': [{"event": alert.event}, {"correlatedEvents": alert.event}]},
                                       {"severity": 1, "_id": 0})['severity']

    def get_count(self, query=None):

        return self.db.alerts.find(query).count()

    def get_alerts(self, query=None, sort=None, limit=0):

        query = query or dict()
        sort = sort or dict()

        responses = self.db.alerts.find(query, sort=sort).limit(limit)
        if not responses:
            LOG.warning('Alert not found with query = %s, sort = %s, limit = %s', query, sort, limit)
            return None

        alerts = list()
        for response in responses:
            alerts.append(
                Alert(
                    alertid=response['_id'],
                    resource=response['resource'],
                    event=response['event'],
                    correlate=response['correlatedEvents'],
                    group=response['group'],
                    value=response['value'],
                    status=response['status'],
                    severity=response['severity'],
                    previous_severity=response['previousSeverity'],
                    environment=response['environment'],
                    service=response['service'],
                    text=response['text'],
                    event_type=response['type'],
                    tags=response['tags'],
                    origin=response['origin'],
                    repeat=response['repeat'],
                    duplicate_count=response['duplicateCount'],
                    threshold_info=response['thresholdInfo'],
                    summary=response['summary'],
                    timeout=response['timeout'],
                    last_receive_id=response['lastReceiveId'],
                    create_time=response['createTime'],
                    expire_time=response['expireTime'],
                    receive_time=response['receiveTime'],
                    last_receive_time=response['lastReceiveTime'],
                    trend_indication=response['trendIndication'],
                    raw_data=response['rawData'],
                    more_info=response['moreInfo'],
                    graph_urls=response['graphUrls'],
                    history=response['history'],
                )
            )
        return alerts

    def get_alert(self, alertid=None, environment=None, resource=None, event=None, severity=None):

        if alertid:
            response = self.db.alerts.find_one({'_id': {'$regex': '^' + alertid}})
        elif severity:
            response = self.db.alerts.find_one({"environment": environment, "resource": resource, "event": event, "severity": severity})
        else:
            response = self.db.alerts.find_one({"environment": environment, "resource": resource, "event": event})

        if not response:
            LOG.warning('Alert not found with environment, resource, event, severity = %s %s %s %s', environment, resource, event, severity)
            return None

        return Alert(
            resource=response.get('resource', None),
            event=response.get('event', None),
            correlate=response.get('correlatedEvents', None),
            group=response.get('group', None),
            value=response.get('value', None),
            status=response.get('status', None),
            severity=response.get('severity', None),
            previous_severity=response.get('previousSeverity', None),
            environment=response.get('environment', None),
            service=response.get('service', None),
            text=response.get('text', None),
            event_type=response.get('type', None),
            tags=response.get('tags', None),
            origin=response.get('origin', None),
            repeat=response.get('repeat', None),
            duplicate_count=response.get('duplicateCount', None),
            threshold_info=response.get('thresholdInfo', None),
            summary=response.get('summary', None),
            timeout=response.get('timeout', None),
            alertid=response.get('_id', None),
            last_receive_id=response.get('lastReceiveId', None),
            create_time=response.get('createTime', None),
            expire_time=response.get('expireTime', None),
            receive_time=response.get('receiveTime', None),
            last_receive_time=response.get('lastReceiveTime', None),
            trend_indication=response.get('trendIndication', None),
            raw_data=response.get('rawData', None),
            more_info=response.get('moreInfo', None),
            graph_urls=response.get('graphUrls', None),
            history=response.get('history', None),
        )

    def update_alert(self, alert, previous_severity=None, trend_indication=None):

        update = {
            "event": alert.event,
            "severity": alert.severity,
            "createTime": alert.create_time,
            "receiveTime": alert.receive_time,
            "lastReceiveTime": alert.receive_time,
            "expireTime": alert.expire_time,
            "previousSeverity": previous_severity,
            "lastReceiveId": alert.alertid,
            "text": alert.text,
            "summary": alert.summary,
            "value": alert.value,
            "tags": alert.tags,
            "repeat": False,
            "origin": alert.origin,
            "thresholdInfo": alert.threshold_info,
            "trendIndication": trend_indication,
            "rawData": alert.raw_data,
            "duplicateCount": 0,
        }

        query = {"environment": alert.environment, "resource": alert.resource,
                     '$or': [{"event": alert.event}, {"correlatedEvents": alert.event}]}

        # FIXME - no native find_and_modify method in this version of pymongo
        no_obj_error = "No matching object found"
        response = self.db.command("findAndModify", 'alerts',
                                   allowable_errors=[no_obj_error],
                                   query=query,
                                   update={'$set': update,
                                           '$push': {
                                               "history": {
                                                    "createTime": update['createTime'],
                                                    "receiveTime": update['receiveTime'],
                                                    "severity": update['severity'],
                                                    "event": update['event'],
                                                    "value": update['value'],
                                                    "text": update['text'],
                                                    "id": update['lastReceiveId']
                                               }
                                           }
                                           },
                                   new=True,
                                   fields={"history": 0})['value']

        return Alert(
            alertid=response['_id'],
            resource=response['resource'],
            event=response['event'],
            correlate=response['correlatedEvents'],
            group=response['group'],
            value=response['value'],
            status=response['status'],
            severity=response['severity'],
            previous_severity=response['previousSeverity'],
            environment=response['environment'],
            service=response['service'],
            text=response['text'],
            event_type=response['type'],
            tags=response['tags'],
            origin=response['origin'],
            repeat=response['repeat'],
            duplicate_count=response['duplicateCount'],
            threshold_info=response['thresholdInfo'],
            summary=response['summary'],
            timeout=response['timeout'],
            last_receive_id=response['lastReceiveId'],
            create_time=response['createTime'],
            expire_time=response['expireTime'],
            receive_time=response['receiveTime'],
            last_receive_time=response['lastReceiveTime'],
            trend_indication=response['trendIndication'],
            raw_data=response['rawData'],
            more_info=response['moreInfo'],
            graph_urls=response['graphUrls'],
        )

    def partial_update_alert(self, alertid=None, alert=None, update=None):

        if alertid:
            query = {'_id': {'$regex': '^' + alertid}}
        else:
            query = {"environment": alert.environment, "resource": alert.resource,
                     '$or': [{"event": alert.event}, {"correlatedEvents": alert.event}]}

        response = self.db.alerts.update(query, {'$set': update}, multi=False)

        if 'status' in update:
            self.update_status(alertid=alertid, alert=alert, status=update['status'])

        return True if 'ok' in response else False

    def delete_alert(self, alertid):

        response = self.db.alerts.remove({'_id': {'$regex': '^' + alertid}})

        return True if 'ok' in response else False

    def tag_alert(self, alertid, tag):

        response = self.db.alerts.update({'_id': {'$regex': '^' + alertid}}, {'$push': {"tags": tag}})

        return True if 'ok' in response else False

    def save_alert(self, alert):

        body = alert.get_body()
        body['history'] = [{
            "id": alert.alertid,
            "event": alert.event,
            "severity": alert.severity,
            "value": alert.value,
            "text": alert.text,
            "createTime": alert.create_time,
            "receiveTime": alert.receive_time,
        }]
        body['_id'] = body['id']
        del body['id']

        return self.db.alerts.insert(body)

    def duplicate_alert(self, alert):

        update = {
            "lastReceiveTime": alert.receive_time,
            "expireTime": alert.expire_time,
            "lastReceiveId": alert.alertid,
            "text": alert.text,
            "summary": alert.summary,
            "value": alert.value,
            "repeat": True,
            "origin": alert.origin,
            "rawData": alert.raw_data,
        }

        # FIXME - no native find_and_modify method in this version of pymongo
        no_obj_error = "No matching object found"
        response = self.db.command("findAndModify", 'alerts',
                                   allowable_errors=[no_obj_error],
                                   query={"environment": alert.environment, "resource": alert.resource, "event": alert.event},
                                   update={'$set': update,
                                           '$inc': {"duplicateCount": 1}
                                   },
                                   new=True,
                                   fields={"history": 0})['value']

        return Alert(
            alertid=response['_id'],
            resource=response['resource'],
            event=response['event'],
            correlate=response['correlatedEvents'],
            group=response['group'],
            value=response['value'],
            status=response['status'],
            severity=response['severity'],
            previous_severity=response['previousSeverity'],
            environment=response['environment'],
            service=response['service'],
            text=response['text'],
            event_type=response['type'],
            tags=response['tags'],
            origin=response['origin'],
            repeat=response['repeat'],
            duplicate_count=response['duplicateCount'],
            threshold_info=response['thresholdInfo'],
            summary=response['summary'],
            timeout=response['timeout'],
            last_receive_id=response['lastReceiveId'],
            create_time=response['createTime'],
            expire_time=response['expireTime'],
            receive_time=response['receiveTime'],
            last_receive_time=response['lastReceiveTime'],
            trend_indication=response['trendIndication'],
            raw_data=response['rawData'],
            more_info=response['moreInfo'],
            graph_urls=response['graphUrls'],
        )

    def update_status(self, alertid=None, alert=None, status=None):

        update_time = datetime.datetime.utcnow()
        update_time = update_time.replace(tzinfo=pytz.utc)

        if alertid:
            query = {"_id": alertid}
        else:
            query = {"environment": alert.environment, "resource": alert.resource,
                     '$or': [{"event": alert.event}, {"correlatedEvents": alert.event}]}

        update = {'$set': {"status": status}, '$push': {"history": {"status": status, "updateTime": update_time}}}

        try:
            self.db.alerts.update(query, update)
        except pymongo.errors.OperationFailure, e:
            LOG.error('MongoDB error: %s', e)

    def get_resources(self, query=None, sort=None, limit=0):

        query = query or dict()
        sort = sort or dict()

        response = self.db.alerts.find(query, sort=sort).limit(limit)
        if not response:
            LOG.warning('No resources found with query = %s, sort = %s, limit = %s', query, sort, limit)
            return None

        unique_resources = dict()  # resources are unique to an environment
        resources = list()
        for resource in response:
            if (tuple(resource['environment']), resource['resource']) not in unique_resources:
                resources.append({
                    'environment': resource['environment'],
                    'resource': resource['resource'],
                    'service': resource['service']
                })
                unique_resources[tuple(resource['environment']), resource['resource']] = True

        return resources

    def get_heartbeats(self):

        heartbeats = list()

        for heartbeat in self.db.heartbeats.find({}, {"_id": 0}):
            heartbeats.append(heartbeat)
        return heartbeats

    def update_hb(self, heartbeat):

        query = {"origin": heartbeat.origin}
        update = {"origin": heartbeat.origin, "version": heartbeat.version, "createTime": heartbeat.create_time,
                  "receiveTime": heartbeat.receive_time}

        try:
            self.db.heartbeats.update(query, update, True)
        except pymongo.errors.OperationFailure, e:
            LOG.error('MongoDB error: %s', e)

    def get_metrics(self):

        metrics = list()

        for stat in self.db.metrics.find({}, {"_id": 0}):
            metrics.append(stat)
        return metrics

    def update_metrics(self, create_time, receive_time):

        # receive latency
        delta = receive_time - create_time
        latency = int(delta.days * 24 * 60 * 60 * 1000 + delta.seconds * 1000 + delta.microseconds / 1000)

        try:
            self.db.metrics.update(
                {
                    "group": "alerts",
                    "name": "received",
                    "type": "timer",
                    "title": "Alert receive rate and latency",
                    "description": "Time taken for alert to be received by the server"
                },
                {
                    '$inc': {"count": 1, "totalTime": latency}
                },
                True)
        except pymongo.errors.OperationFailure, e:
            LOG.error('MongoDB error: %s', e)

        # processing latency
        delta = datetime.datetime.utcnow() - receive_time
        latency = int(delta.days * 24 * 60 * 60 * 1000 + delta.seconds * 1000 + delta.microseconds / 1000)

        try:
            self.db.metrics.update(
                {
                    "group": "alerts",
                    "name": "processed",
                    "type": "timer",
                    "title": "Alert process rate and duration",
                    "description": "Time taken to process the alert on the server"
                },
                {
                    '$inc': {"count": 1, "totalTime": latency}
                },
                True)
        except pymongo.errors.OperationFailure, e:
            LOG.error('MongoDB error: %s', e)

    def disconnect(self):

        if self.conn.alive():
            self.conn.disconnect()

        LOG.info('Mongo disconnected.')
