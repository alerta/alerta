import os
import sys
import datetime
import base64
import hmac
import random
import hashlib

import pymongo

from alerta.app import app, severity_code, status_code

from alerta.alert import AlertDocument
from alerta.heartbeat import HeartbeatDocument


LOG = app.logger


class Mongo(object):

    def __init__(self):

        self.db = None
        self.conn = None
        self.connect()

    def connect(self):

        if 'MONGO_PORT' in os.environ and 'tcp://' in os.environ['MONGO_PORT']:  # used by linked Docker containers
            host, port = os.environ['MONGO_PORT'][6:].split(':')
            app.config['MONGO_HOST'] = host
            app.config['MONGO_PORT'] = int(port)

        if not app.config['MONGO_REPLSET']:
            try:
                self.conn = pymongo.MongoClient(app.config['MONGO_HOST'], app.config['MONGO_PORT'])
            except Exception, e:
                LOG.error('MongoDB Client connection error - %s:%s : %s', app.config['MONGO_HOST'], app.config['MONGO_PORT'], e)
                sys.exit(1)
            LOG.info('Connected to mongodb://%s:%s/%s', app.config['MONGO_HOST'], app.config['MONGO_PORT'], app.config['MONGO_DATABASE'])
        else:
            try:
                self.conn = pymongo.MongoClient(app.config['MONGO_HOST'], app.config['MONGO_PORT'], replicaSet=app.config['MONGO_REPLSET'])
            except Exception, e:
                LOG.error('MongoDB Client ReplicaSet connection error - %s:%s (replicaSet=%s) : %s',
                          app.config['MONGO_HOST'], app.config['MONGO_PORT'], app.config['MONGO_REPLSET'], e)
                sys.exit(1)
            LOG.info('Connected to mongodb://%s:%s/%s?replicaSet=%s',
                     app.config['MONGO_HOST'], app.config['MONGO_PORT'], app.config['MONGO_DATABASE'], app.config['MONGO_REPLSET'])

        self.db = self.conn[app.config['MONGO_DATABASE']]

        if app.config['MONGO_PASSWORD']:
            try:
                self.db.authenticate(app.config['MONGO_USERNAME'], password=app.config['MONGO_PASSWORD'])
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

        self.db.tokens.ensure_index([('expireTime', pymongo.ASCENDING)], expireAfterSeconds=0)

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
                "createTime": alert.create_time,
                "rawData": alert.raw_data,
                "duplicateCount": 0,
                "repeat": False,
                "previousSeverity": previous_severity,
                "trendIndication": trend_indication,
                "receiveTime": now,
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

    def create_alert(self, alert):

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
                    "event": event,
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

    def untag_alert(self, id, tags):
        """
        Remove tags from tag list.
        """
        response = self.db.alerts.update({'_id': {'$regex': '^' + id}}, {'$pullAll': {"tags": tags}})

        return True if 'ok' in response else False

    def delete_alert(self, id):

        response = self.db.alerts.remove({'_id': {'$regex': '^' + id}})

        return True if 'ok' in response else False

    def get_counts(self, query=None):
        """
        Return total and dict() of severity and status counts.
        """

        return self.db.alerts.find(query, {"severity": 1, "status": 1})

    def get_topn(self, query=None, group=None, limit=10):

        if not group:
            group = "event"  # group by event is nothing specified

        pipeline = [
            {'$match': query},
            {'$unwind': '$service'},
            {
                '$group': {
                    "_id": "$%s" % group,
                    "count": {'$sum': 1},
                    "duplicateCount": {'$sum': "$duplicateCount"},
                    "environments": {'$addToSet': "$environment"},
                    "services": {'$addToSet': "$service"},
                    "resources": {'$addToSet': {"id": "$_id", "resource": "$resource"}}
                }
            },
            {'$sort': {"count": -1, "duplicateCount": -1}},
            {'$limit': limit}
        ]

        responses = self.db.alerts.aggregate(pipeline)

        top = list()
        for response in responses['result']:
            top.append(
                {
                    "%s" % group: response['_id'],
                    "environments": response['environments'],
                    "services": response['services'],
                    "resources": response['resources'],
                    "count": response['count'],
                    "duplicateCount": response['duplicateCount']
                }
            )
        return top

    def get_environments(self, query=None, fields=None, limit=0):

        if fields:
            fields['environment'] = 1
        else:
            fields = {"environment": 1}

        pipeline = [
            {'$match': query},
            {'$project': fields},
            {'$limit': limit},
            {'$group': {"_id": "$environment", "count": {'$sum': 1}}}
        ]

        responses = self.db.alerts.aggregate(pipeline)

        environments = list()
        for response in responses['result']:
            environments.append(
                {
                    "environment": response['_id'],
                    "count": response['count']
                }
            )
        return environments

    def get_services(self, query=None, fields=None, limit=0):

        if not fields:
            fields = {
                "environment": 1,
                "service": 1
            }

        pipeline = [
            {'$unwind': '$service'},
            {'$match': query},
            {'$project': fields},
            {'$limit': limit},
            {'$group': {"_id": {"environment": "$environment", "service": "$service"}, "count": {'$sum': 1}}}
        ]

        responses = self.db.alerts.aggregate(pipeline)

        services = list()
        for response in responses['result']:
            services.append(
                {
                    "environment": response['_id']['environment'],
                    "service": response['_id']['service'],
                    "count": response['count']
                }
            )
        return services

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

    def get_users(self):

        users = list()

        for user in self.db.users.find({}, {"_id": 0}):
            users.append(user)
        return users

    def is_user_valid(self, user):

        return bool(self.db.users.find_one({"user": user}))

    def save_user(self, args):

        data = {
            "user": args["user"],
            "createTime": datetime.datetime.utcnow(),
            "sponsor": args["sponsor"]
        }

        return self.db.users.insert(data)

    def delete_user(self, user):

        response = self.db.users.remove({"user": user})
        return True if 'ok' in response else False

    def get_metrics(self):

        metrics = list()

        for stat in self.db.metrics.find({}, {"_id": 0}):
            metrics.append(stat)
        return metrics

    def get_keys(self, query=None):

        responses = self.db.keys.find(query)
        keys = list()
        for response in responses:
            keys.append(
                {
                    "user": response["user"],
                    "key": response["key"],
                    "text": response["text"],
                    "expireTime": response["expireTime"],
                    "count": response["count"],
                    "lastUsedTime": response["lastUsedTime"]
                }
            )

        return keys

    def is_key_valid(self, key):

        key_info = self.db.keys.find_one({"key": key})

        if key_info:
            if key_info['expireTime'] > datetime.datetime.utcnow():
                return True
            else:
                return False
        else:
            return False

    def create_key(self, args):

        digest = hmac.new(app.config['SECRET_KEY'], msg=str(random.getrandbits(32)), digestmod=hashlib.sha256).digest()
        key = base64.b64encode(digest)[:40]

        if 'user' not in args:
            return None

        data = {
            "user": args["user"],
            "key": key,
            "text": args.get('text', None),
            "expireTime": datetime.datetime.utcnow() + datetime.timedelta(days=args.get('days', app.config['API_KEY_EXPIRE_DAYS'])),
            "count": 0,
            "lastUsedTime": None
        }

        response = self.db.keys.insert(data)
        if not response:
            return None

        return key

    def update_key(self, key):

        self.db.keys.update(
            {
                "key": key
            },
            {
                '$set': {"lastUsedTime": datetime.datetime.utcnow()},
                '$inc': {"count": 1}
            },
            True
        )

    def delete_key(self, key):

        response = self.db.keys.remove({"key": key})
        return True if 'ok' in response else False

    def is_token_valid(self, token):

        return bool(self.db.tokens.find_one({"token": token}))

    def save_token(self, token):

        data = {
            "token": token,
            "expireTime": datetime.datetime.utcnow() + datetime.timedelta(minutes=app.config['ACCESS_TOKEN_CACHE_MINS'])
        }

        return self.db.tokens.insert(data)

    def disconnect(self):

        if self.conn.alive():
            self.conn.disconnect()

        LOG.info('Mongo disconnected.')
