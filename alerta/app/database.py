
import sys
import datetime
import pymongo

from alerta.common import log as logging
from alerta.common import config
from alerta.common.alert import AlertDocument
from alerta.common.heartbeat import HeartbeatDocument
from alerta.common import severity_code, status_code

LOG = logging.getLogger(__name__)
CONF = config.CONF


class Mongo(object):

    mongo_opts = {
        'mongo_host': 'localhost',
        'mongo_port': 27017,
        'mongo_database': 'monitoring',
        'mongo_username': 'admin',
        'mongo_password': '',
    }

    def __init__(self):

        config.register_opts(Mongo.mongo_opts)

        self.db = None
        self.conn = None
        self.connect()

    def connect(self):

        # Connect to MongoDB
        try:
            self.conn = pymongo.MongoClient(CONF.mongo_host, CONF.mongo_port)  # version >= 2.4
        except AttributeError:
            self.conn = pymongo.Connection(CONF.mongo_host, CONF.mongo_port)  # version < 2.4
        except Exception, e:
            LOG.error('MongoDB Client connection error : %s', e)
            sys.exit(1)

        try:
            self.db = self.conn[CONF.mongo_database]
        except Exception, e:
            LOG.error('MongoDB database error : %s', e)
            sys.exit(1)

        LOG.info('Connected to mongodb://%s:%s/%s', CONF.mongo_host, CONF.mongo_port, CONF.mongo_database)

        if CONF.mongo_password:
            try:
                self.db.authenticate(CONF.mongo_username, password=CONF.mongo_password)
            except Exception, e:
                LOG.error('MongoDB authentication failed: %s', e)
                sys.exit(1)

        LOG.info('Available MongoDB collections: %s', ','.join(self.db.collection_names()))

        self.create_indexes()

    def create_indexes(self):

        self.db.alerts.create_index([('environment', pymongo.ASCENDING), ('resource', pymongo.ASCENDING),
                                     ('event', pymongo.ASCENDING), ('severity', pymongo.ASCENDING)])
        self.db.alerts.create_index([('status', pymongo.ASCENDING), ('lastReceiveTime', pymongo.ASCENDING)])
        self.db.alerts.create_index([('status', pymongo.ASCENDING), ('lastReceiveTime', pymongo.ASCENDING),
                                     ('environment', pymongo.ASCENDING)])
        self.db.alerts.create_index([('status', pymongo.ASCENDING), ('service', pymongo.ASCENDING)])
        self.db.alerts.create_index([('status', pymongo.ASCENDING), ('environment', pymongo.ASCENDING)])
        self.db.alerts.create_index([('status', pymongo.ASCENDING), ('expireTime', pymongo.ASCENDING)])
        self.db.alerts.create_index([('status', pymongo.ASCENDING)])

    def get_severity(self, alert):
        """
        Get severity of correlated alert. Used to determine previous severity.
        """
        query = {
            "environment": alert.environment,
            "resource": alert.resource,
            '$or': [
                {
                    "event": alert.event,
                    "severity": {'$ne': alert.severity}
                },
                {
                    "event": {'$ne': alert.event},
                    "correlate": alert.event,
                    "severity": alert.severity
                },
                {
                    "event": {'$ne': alert.event},
                    "correlate": alert.event,
                    "severity": {'$ne': alert.severity}
                }]
        }

        return self.db.alerts.find_one(query, fields={"severity": 1, "_id": 0})['severity']

    def get_status(self, alert):
        """
        Get status of correlated or duplicate alert. Used to determine previous status.
        """
        query = {
            "environment": alert.environment,
            "resource": alert.resource,
            '$or': [
                {
                    "event": alert.event
                },
                {
                    "correlate": alert.event,
                }
            ]
        }

        return self.db.alerts.find_one(query, fields={"status": 1, "_id": 0})['status']

    def get_count(self, query=None):
        """
        Return total number of alerts that meet the query filter.
        """
        return self.db.alerts.find(query).count()

    def get_alerts(self, query=None, fields=None, sort=None, limit=0):

        responses = self.db.alerts.find(query, fields=fields, sort=sort).limit(limit)

        alerts = list()
        for response in responses:
            alerts.append(
                AlertDocument(
                    id=response['_id'],
                    resource=response['resource'],
                    event=response['event'],
                    environment=response['environment'],
                    severity=response['severity'],
                    correlate=response['correlate'],
                    status=response['status'],
                    service=response['service'],
                    group=response['group'],
                    value=response['value'],
                    text=response['text'],
                    tags=response['tags'],
                    attributes=response['attributes'],
                    origin=response['origin'],
                    event_type=response['type'],
                    create_time=response['createTime'],
                    timeout=response['timeout'],
                    raw_data=response['rawData'],
                    duplicate_count=response['duplicateCount'],
                    repeat=response['repeat'],
                    previous_severity=response['previousSeverity'],
                    trend_indication=response['trendIndication'],
                    receive_time=response['receiveTime'],
                    last_receive_id=response['lastReceiveId'],
                    last_receive_time=response['lastReceiveTime'],
                    history=response['history']
                )
            )
        return alerts

    def get_history(self, query=None, fields=None, limit=0):

        if not fields:
            fields = {
                "resource": 1,
                "event": 1,
                "environment": 1,
                "service": 1,
                "group": 1,
                "tags": 1,
                "attributes": 1,
                "origin": 1,
                "type": 1,
                "history": 1
            }

        pipeline = [
            {'$match': query},
            {'$unwind': '$history'},
            {'$project': fields},
            {'$limit': limit},
            {'$sort': {'history.updateTime': 1}}
        ]

        responses = self.db.alerts.aggregate(pipeline)

        history = list()
        for response in responses['result']:
            if 'severity' in response['history']:
                history.append(
                    {
                        "id": response['_id'],  # or response['history']['id']
                        "resource": response['resource'],
                        "event": response['history']['event'],
                        "environment": response['environment'],
                        "severity": response['history']['severity'],
                        "service": response['service'],
                        "group": response['group'],
                        "value": response['history']['value'],
                        "text": response['history']['text'],
                        "tags": response['tags'],
                        "attributes": response['attributes'],
                        "origin": response['origin'],
                        "type": response['type'],
                        "updateTime": response['history']['updateTime']
                    }
                )
            elif 'status' in response['history']:
                history.append(
                    {
                        "id": response['_id'],  # or response['history']['id']
                        "resource": response['resource'],
                        "event": response['event'],
                        "environment": response['environment'],
                        "status": response['history']['status'],
                        "service": response['service'],
                        "group": response['group'],
                        "text": response['history']['text'],
                        "tags": response['tags'],
                        "attributes": response['attributes'],
                        "origin": response['origin'],
                        "type": response['type'],
                        "updateTime": response['history']['updateTime']
                    }
                )
        return history

    def is_duplicate(self, alert):

        query = {
            "environment": alert.environment,
            "resource": alert.resource,
            "event": alert.event,
            "severity": alert.severity
        }

        return bool(self.db.alerts.find_one(query))

    def is_correlated(self, alert):

        query = {
            "environment": alert.environment,
            "resource": alert.resource,
            '$or': [
                {
                    "event": alert.event,
                    "severity": {'$ne': alert.severity}
                },
                {
                    "event": {'$ne': alert.event},
                    "correlate": alert.event,
                    "severity": alert.severity
                },
                {
                    "event": {'$ne': alert.event},
                    "correlate": alert.event,
                    "severity": {'$ne': alert.severity}
                }]
        }

        return bool(self.db.alerts.find_one(query))

    def save_duplicate(self, alert):
        """
        Update alert value, text and rawData, increment duplicate count and set repeat=True, and
        keep track of last receive id and time but don't append to history unless status changes.
        """

        previous_status = self.get_status(alert)
        if alert.status != status_code.UNKNOWN and alert.status != previous_status:
            status = alert.status
        else:
            status = previous_status

        query = {
            "environment": alert.environment,
            "resource": alert.resource,
            "event": alert.event,
            "severity": alert.severity
        }

        now = datetime.datetime.utcnow()
        update = {
            '$set': {
                "status": status,
                "value": alert.value,
                "text": alert.text,
                "rawData": alert.raw_data,
                "repeat": True,
                "lastReceiveId": alert.id,
                "lastReceiveTime": now
            },
            '$inc': {"duplicateCount": 1}
        }
        if status != previous_status:
            update['$push'] = {
                "history": {
                    "event": alert.event,
                    "status": status,
                    "text": "duplicate alert status change",
                    "id": alert.id,
                    "updateTime": now
                }
            }

        LOG.debug('Update duplicate alert in database: %s', update)

        no_obj_error = "No matching object found"
        response = self.db.command("findAndModify", 'alerts',
                                   allowable_errors=[no_obj_error],
                                   query=query,
                                   update=update,
                                   new=True,
                                   fields={"history": 0}
                                   )["value"]

        return AlertDocument(
            id=response['_id'],
            resource=response['resource'],
            event=response['event'],
            environment=response['environment'],
            severity=response['severity'],
            correlate=response['correlate'],
            status=response['status'],
            service=response['service'],
            group=response['group'],
            value=response['value'],
            text=response['text'],
            tags=response['tags'],
            attributes=response['attributes'],
            origin=response['origin'],
            event_type=response['type'],
            create_time=response['createTime'],
            timeout=response['timeout'],
            raw_data=response['rawData'],
            duplicate_count=response['duplicateCount'],
            repeat=response['repeat'],
            previous_severity=response['previousSeverity'],
            trend_indication=response['trendIndication'],
            receive_time=response['receiveTime'],
            last_receive_id=response['lastReceiveId'],
            last_receive_time=response['lastReceiveTime'],
            history=list()
        )

    def save_correlated(self, alert):
        """
        Update alert key attributes, reset duplicate count and set repeat=False, keep track of last
        receive id and time, appending all to history. Append to history again if status changes.
        """

        previous_severity = self.get_severity(alert)
        previous_status = self.get_status(alert)
        trend_indication = severity_code.trend(previous_severity, alert.severity)
        if alert.status == status_code.UNKNOWN:
            status = severity_code.status_from_severity(previous_severity, alert.severity, previous_status)
        else:
            status = alert.status

        query = {
            "environment": alert.environment,
            "resource": alert.resource,
            '$or': [
                {
                    "event": alert.event,
                    "severity": {'$ne': alert.severity}
                },
                {
                    "event": {'$ne': alert.event},
                    "correlate": alert.event,
                    "severity": alert.severity
                },
                {
                    "event": {'$ne': alert.event},
                    "correlate": alert.event,
                    "severity": {'$ne': alert.severity}
                }]
        }

        now = datetime.datetime.utcnow()
        update = {
            '$set': {
                "event": alert.event,
                "severity": alert.severity,
                "status": status,
                "value": alert.value,
                "text": alert.text,
                "rawData": alert.raw_data,
                "duplicateCount": 0,
                "repeat": False,
                "previousSeverity": previous_severity,
                "trendIndication": trend_indication,
                "lastReceiveId": alert.id,
                "lastReceiveTime": now
            },
            '$pushAll': {
                "history": [{
                    "event": alert.event,
                    "severity": alert.severity,
                    "value": alert.value,
                    "text": alert.text,
                    "id": alert.id,
                    "updateTime": alert.create_time
                }]
            }
        }

        if status != previous_status:
            update['$pushAll']['history'].append({
                "event": alert.event,
                "status": status,
                "text": "correlated alert status change",
                "id": alert.id,
                "updateTime": now
            })

        LOG.debug('Update correlated alert in database: %s', update)

        no_obj_error = "No matching object found"
        response = self.db.command("findAndModify", 'alerts',
                                   allowable_errors=[no_obj_error],
                                   query=query,
                                   update=update,
                                   new=True,
                                   fields={"history": 0}
                                   )["value"]

        return AlertDocument(
            id=response['_id'],
            resource=response['resource'],
            event=response['event'],
            environment=response['environment'],
            severity=response['severity'],
            correlate=response['correlate'],
            status=response['status'],
            service=response['service'],
            group=response['group'],
            value=response['value'],
            text=response['text'],
            tags=response['tags'],
            attributes=response['attributes'],
            origin=response['origin'],
            event_type=response['type'],
            create_time=response['createTime'],
            timeout=response['timeout'],
            raw_data=response['rawData'],
            duplicate_count=response['duplicateCount'],
            repeat=response['repeat'],
            previous_severity=response['previousSeverity'],
            trend_indication=response['trendIndication'],
            receive_time=response['receiveTime'],
            last_receive_id=response['lastReceiveId'],
            last_receive_time=response['lastReceiveTime'],
            history=list()
        )

    def save_alert(self, alert):

        trend_indication = severity_code.trend(severity_code.UNKNOWN, alert.severity)
        if alert.status == status_code.UNKNOWN:
                    status = severity_code.status_from_severity(severity_code.UNKNOWN, alert.severity)
        else:
            status = alert.status

        now = datetime.datetime.utcnow()
        history = [{
            "id": alert.id,
            "event": alert.event,
            "severity": alert.severity,
            "value": alert.value,
            "text": alert.text,
            "updateTime": alert.create_time
        }]
        if status != alert.status:
            history.append({
                "event": alert.event,
                "status": status,
                "text": "new alert status change",
                "id": alert.id,
                "updateTime": now
            })

        alert = {
            "_id": alert.id,
            "resource": alert.resource,
            "event": alert.event,
            "environment": alert.environment,
            "severity": alert.severity,
            "correlate": alert.correlate,
            "status": status,
            "service": alert.service,
            "group": alert.group,
            "value": alert.value,
            "text": alert.text,
            "tags": alert.tags,
            "attributes": alert.attributes,
            "origin": alert.origin,
            "type": alert.event_type,
            "createTime": alert.create_time,
            "timeout": alert.timeout,
            "rawData": alert.raw_data,
            "duplicateCount": 0,
            "repeat": False,
            "previousSeverity": severity_code.UNKNOWN,
            "trendIndication": trend_indication,
            "receiveTime": now,
            "lastReceiveId": alert.id,
            "lastReceiveTime": now,
            "history": history
        }

        LOG.debug('Insert new alert in database: %s', alert)

        response = self.db.alerts.insert(alert)

        if not response:
            return

        return AlertDocument(
            id=alert['_id'],
            resource=alert['resource'],
            event=alert['event'],
            environment=alert['environment'],
            severity=alert['severity'],
            correlate=alert['correlate'],
            status=alert['status'],
            service=alert['service'],
            group=alert['group'],
            value=alert['value'],
            text=alert['text'],
            tags=alert['tags'],
            attributes=alert['attributes'],
            origin=alert['origin'],
            event_type=alert['type'],
            create_time=alert['createTime'],
            timeout=alert['timeout'],
            raw_data=alert['rawData'],
            duplicate_count=alert['duplicateCount'],
            repeat=alert['repeat'],
            previous_severity=alert['previousSeverity'],
            trend_indication=alert['trendIndication'],
            receive_time=alert['receiveTime'],
            last_receive_id=alert['lastReceiveId'],
            last_receive_time=alert['lastReceiveTime'],
            history=list()
        )

    def get_alert(self, id):

        if len(id) == 8:
            query = {'$or': [{'_id': {'$regex': '^' + id}}, {'lastReceiveId': {'$regex': '^' + id}}]}
        else:
            query = {'$or': [{'_id': id}, {'lastReceiveId': id}]}

        response = self.db.alerts.find_one(query)
        if not response:
            return

        return AlertDocument(
            id=response['_id'],
            resource=response['resource'],
            event=response['event'],
            environment=response['environment'],
            severity=response['severity'],
            correlate=response['correlate'],
            status=response['status'],
            service=response['service'],
            group=response['group'],
            value=response['value'],
            text=response['text'],
            tags=response['tags'],
            attributes=response['attributes'],
            origin=response['origin'],
            event_type=response['type'],
            create_time=response['createTime'],
            timeout=response['timeout'],
            raw_data=response['rawData'],
            duplicate_count=response['duplicateCount'],
            repeat=response['repeat'],
            previous_severity=response['previousSeverity'],
            trend_indication=response['trendIndication'],
            receive_time=response['receiveTime'],
            last_receive_id=response['lastReceiveId'],
            last_receive_time=response['lastReceiveTime'],
            history=response['history']
        )

    def set_status(self, id, status, text=None):
        """
        Set status and update history.
        """
        query = {'_id': {'$regex': '^' + id}}

        event = self.db.alerts.find_one(query, fields={"event": 1, "_id": 0})['event']

        now = datetime.datetime.utcnow()
        update = {
            '$set': {"status": status},
            '$push': {
                "history": {
                    "status": event,
                    "status": status,
                    "text": text,
                    "id": id,
                    "updateTime": now
                }
            }
        }

        no_obj_error = "No matching object found"
        response = self.db.command("findAndModify", 'alerts',
                                   allowable_errors=[no_obj_error],
                                   query=query,
                                   update=update,
                                   new=True,
                                   fields={"history": 0}
                                   )["value"]

        return AlertDocument(
            id=response['_id'],
            resource=response['resource'],
            event=response['event'],
            environment=response['environment'],
            severity=response['severity'],
            correlate=response['correlate'],
            status=response['status'],
            service=response['service'],
            group=response['group'],
            value=response['value'],
            text=response['text'],
            tags=response['tags'],
            attributes=response['attributes'],
            origin=response['origin'],
            event_type=response['type'],
            create_time=response['createTime'],
            timeout=response['timeout'],
            raw_data=response['rawData'],
            duplicate_count=response['duplicateCount'],
            repeat=response['repeat'],
            previous_severity=response['previousSeverity'],
            trend_indication=response['trendIndication'],
            receive_time=response['receiveTime'],
            last_receive_id=response['lastReceiveId'],
            last_receive_time=response['lastReceiveTime'],
            history=list()
        )

    def tag_alert(self, id, tags):
        """
        Append tags to tag list. Don't add same tag more than once.
        """
        response = self.db.alerts.update({'_id': {'$regex': '^' + id}}, {'$addToSet': {"tags": {'$each': tags}}})

        return True if 'ok' in response else False

    def delete_alert(self, id):

        response = self.db.alerts.remove({'_id': {'$regex': '^' + id}})

        return True if 'ok' in response else False

    def get_counts(self, query=None):
        """
        Return total and dict() of severity and status counts.
        """

        return self.db.alerts.find(query, {"severity": 1, "status": 1})

    def get_heartbeats(self):

        responses = self.db.heartbeats.find()

        heartbeats = list()
        for response in responses:
            heartbeats.append(
                HeartbeatDocument(
                    id=response['_id'],
                    origin=response['origin'],
                    tags=response['tags'],
                    event_type=response['type'],
                    create_time=response['createTime'],
                    timeout=response['timeout'],
                    receive_time=response['receiveTime']
                )
            )
        return heartbeats

    def save_heartbeat(self, heartbeat):

        now = datetime.datetime.utcnow()
        update = {
            #  '$setOnInsert': {"_id": heartbeat.id},
            '$set': {
                "origin": heartbeat.origin,
                "tags": heartbeat.tags,
                "type": heartbeat.event_type,
                "createTime": heartbeat.create_time,
                "timeout": heartbeat.timeout,
                "receiveTime": now
            }
        }

        LOG.debug('Save heartbeat to database: %s', update)

        heartbeat_id = self.db.heartbeats.find_one({"origin": heartbeat.origin}, {})

        if heartbeat_id:
            no_obj_error = "No matching object found"
            response = self.db.command("findAndModify", 'heartbeats',
                                       allowable_errors=[no_obj_error],
                                       query={"origin": heartbeat.origin},
                                       update=update,
                                       new=True,
                                       upsert=True
                                       )["value"]
            return response['_id']
        else:
            update = update['$set']
            update["_id"] = heartbeat.id
            response = self.db.heartbeats.insert(update)
            return response

    def delete_heartbeat(self, id):

        response = self.db.heartbeats.remove({'_id': {'$regex': '^' + id}})

        return True if 'ok' in response else False

    def get_metrics(self):

        metrics = list()

        for stat in self.db.metrics.find({}, {"_id": 0}):
            metrics.append(stat)
        return metrics

    def disconnect(self):

        if self.conn.alive():
            self.conn.disconnect()

        LOG.info('Mongo disconnected.')
