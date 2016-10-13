import os
import sys
import datetime
import base64
import hmac
import hashlib
import bcrypt

from uuid import uuid4
from six import string_types
from pymongo import MongoClient, ASCENDING, TEXT, ReturnDocument

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

from alerta.app import app, severity_code, status_code
from alerta.app.alert import AlertDocument
from alerta.app.heartbeat import HeartbeatDocument


LOG = app.logger


class Mongo(object):

    def __init__(self):

        self.connect()

    def connect(self):

        mongo_uri = (os.environ.get('MONGO_URI', None) or
                     os.environ.get('MONGODB_URI', None) or
                     os.environ.get('MONGOHQ_URL', None) or
                     os.environ.get('MONGOLAB_URI', None))
        if mongo_uri:
            try:
                self._client = MongoClient(mongo_uri, connect=False)
            except Exception as e:
                LOG.error('MongoDB Client connection error - %s : %s', mongo_uri, e)
                sys.exit(1)

            uri = urlparse(mongo_uri)

            app.config['MONGO_HOST'] = uri.hostname
            app.config['MONGO_PORT'] = uri.port
            app.config['MONGO_DATABASE'] = uri.path.lstrip('/')
            app.config['MONGO_REPLSET'] = None

            if uri.username:
                app.config['MONGO_USERNAME'] = uri.username
                app.config['MONGO_PASSWORD'] = uri.password

        elif 'MONGO_PORT' in os.environ and 'tcp://' in os.environ['MONGO_PORT']:  # Docker
            host, port = os.environ['MONGO_PORT'][6:].split(':')
            try:
                self._client = MongoClient(host, int(port), connect=False)
            except Exception as e:
                LOG.error('MongoDB Client connection error - %s : %s', os.environ['MONGO_PORT'], e)
                sys.exit(1)

        elif not app.config['MONGO_REPLSET']:
            try:
                self._client = MongoClient(app.config['MONGO_HOST'], app.config['MONGO_PORT'], connect=False)
            except Exception as e:
                LOG.error('MongoDB Client connection error - %s:%s : %s', app.config['MONGO_HOST'], app.config['MONGO_PORT'], e)
                sys.exit(1)
            LOG.debug('Connected to mongodb://%s:%s/%s', app.config['MONGO_HOST'], app.config['MONGO_PORT'], app.config['MONGO_DATABASE'])

        else:
            try:
                self._client = MongoClient(app.config['MONGO_HOST'], app.config['MONGO_PORT'], replicaSet=app.config['MONGO_REPLSET'], connect=False)
            except Exception as e:
                LOG.error('MongoDB Client ReplicaSet connection error - %s:%s (replicaSet=%s) : %s',
                          app.config['MONGO_HOST'], app.config['MONGO_PORT'], app.config['MONGO_REPLSET'], e)
                sys.exit(1)
            LOG.debug('Connected to mongodb://%s:%s/%s?replicaSet=%s', app.config['MONGO_HOST'],
                      app.config['MONGO_PORT'], app.config['MONGO_DATABASE'], app.config['MONGO_REPLSET'])

        self._db = self._client[app.config['MONGO_DATABASE']]

        if app.config['MONGO_PASSWORD']:
            try:
                self._db.authenticate(app.config['MONGO_USERNAME'], password=app.config['MONGO_PASSWORD'])
            except Exception as e:
                LOG.error('MongoDB authentication failed: %s', e)
                sys.exit(1)

        self._create_indexes()

    def _create_indexes(self):

        self._db.alerts.create_index([('environment', ASCENDING), ('resource', ASCENDING), ('event', ASCENDING)], unique=True)
        self._db.alerts.create_index([('$**', TEXT)])

    def get_db(self):

        return self._db

    def get_info(self):

        return self._db.name

    def get_version(self):

        return self._db.client.server_info()['version']

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
                    "correlate": alert.event
                }],
            "customer": alert.customer
        }

        return self._db.alerts.find_one(query, projection={"severity": 1, "_id": 0})['severity']

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
            ],
            "customer": alert.customer
        }

        return self._db.alerts.find_one(query, projection={"status": 1, "_id": 0})['status']

    def get_count(self, query=None):
        """
        Return total number of alerts that meet the query filter.
        """
        return self._db.alerts.find(query).count()

    def get_alerts(self, query=None, fields=None, sort=None, page=1, limit=0):

        if 'status' not in query:
            query['status'] = {'$ne': "expired"}

        responses = self._db.alerts.find(query, projection=fields, sort=sort).skip((page-1)*limit).limit(limit)

        alerts = list()
        for response in responses:
            alerts.append(
                AlertDocument(
                    id=response['_id'],
                    resource=response['resource'],
                    event=response['event'],
                    environment=response['environment'],
                    severity=response.get('severity'),
                    correlate=response.get('correlate'),
                    status=response.get('status'),
                    service=response.get('service'),
                    group=response.get('group'),
                    value=response.get('value'),
                    text=response.get('text'),
                    tags=response.get('tags'),
                    attributes=response.get('attributes'),
                    origin=response.get('origin'),
                    event_type=response.get('type'),
                    create_time=response.get('createTime'),
                    timeout=response.get('timeout'),
                    raw_data=response.get('rawData'),
                    customer=response.get('customer', None),
                    duplicate_count=response.get('duplicateCount'),
                    repeat=response.get('repeat'),
                    previous_severity=response.get('previousSeverity'),
                    trend_indication=response.get('trendIndication'),
                    receive_time=response.get('receiveTime'),
                    last_receive_id=response.get('lastReceiveId'),
                    last_receive_time=response.get('lastReceiveTime'),
                    history=response.get('history', [])
                )
            )
        return alerts

    def get_history(self, query=None, fields=None, limit=0):

        if not fields:
            fields = {
                "resource": 1,
                "event": 1,
                "environment": 1,
                "customer": 1,
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

        responses = self._db.alerts.aggregate(pipeline)

        history = list()
        for response in responses:
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
                        "updateTime": response['history']['updateTime'],
                        "type": response['history'].get('type', 'unknown'),
                        "customer": response.get('customer', None)
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
                        "updateTime": response['history']['updateTime'],
                        "type": response['history'].get('type', 'unknown'),
                        "customer": response.get('customer', None)
                    }
                )
        return history

    def is_duplicate(self, alert):

        query = {
            "environment": alert.environment,
            "resource": alert.resource,
            "event": alert.event,
            "severity": alert.severity,
            "customer": alert.customer
        }

        return bool(self._db.alerts.find_one(query))

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
                    "correlate": alert.event
                }],
            "customer": alert.customer
        }

        return bool(self._db.alerts.find_one(query))

    def save_duplicate(self, alert):
        """
        Update alert value, text and rawData, increment duplicate count and set repeat=True, and
        keep track of last receive id and time but don't append to history unless status changes.
        """

        previous_status = self.get_status(alert)
        if alert.status != status_code.UNKNOWN and alert.status != previous_status:
            status = alert.status
        else:
            status = status_code.status_from_severity(alert.severity, alert.severity, previous_status)

        query = {
            "environment": alert.environment,
            "resource": alert.resource,
            "event": alert.event,
            "severity": alert.severity,
            "customer": alert.customer
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
            '$addToSet': {"tags": {'$each': alert.tags}},
            '$inc': {"duplicateCount": 1}
        }

        # only update those attributes that are specifically defined
        attributes = {'attributes.'+k: v for k, v in alert.attributes.items()}
        update['$set'].update(attributes)

        if status != previous_status:
            update['$push'] = {
                "history": {
                    '$each': [{
                        "event": alert.event,
                        "status": status,
                        "type": "auto",
                        "text": "duplicate alert status change",
                        "id": alert.id,
                        "updateTime": now
                    }],
                    '$slice': -abs(app.config['HISTORY_LIMIT'])
                }
            }

        LOG.debug('Update duplicate alert in database: %s', update)
        response = self._db.alerts.find_one_and_update(
            query,
            update=update,
            projection={"history": 0},
            return_document=ReturnDocument.AFTER
        )

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
            customer=response.get('customer', None),
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
            status = status_code.status_from_severity(previous_severity, alert.severity, previous_status)
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
                    "correlate": alert.event
                }],
            "customer": alert.customer
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
            '$addToSet': {"tags": {'$each': alert.tags}},
            '$push': {
                "history": {
                    '$each': [{
                        "event": alert.event,
                        "severity": alert.severity,
                        "value": alert.value,
                        "type": "external",
                        "text": alert.text,
                        "id": alert.id,
                        "updateTime": now
                    }],
                    '$slice': -abs(app.config['HISTORY_LIMIT'])
                }
            }
        }

        # only update those attributes that are specifically defined
        attributes = {'attributes.'+k: v for k, v in alert.attributes.items()}
        update['$set'].update(attributes)

        if status != previous_status:
            update['$push']['history']['$each'].append({
                "event": alert.event,
                "status": status,
                "type": "auto",
                "text": "correlated alert status change",
                "id": alert.id,
                "updateTime": now
            })

        LOG.debug('Update correlated alert in database: %s', update)
        response = self._db.alerts.find_one_and_update(
            query,
            update=update,
            projection={"history": 0},
            return_document=ReturnDocument.AFTER
        )

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
            customer=response.get('customer', None),
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
        """
        Create new alert, set duplicate count to zero and set repeat=False, keep track of last
        receive id and time, appending all to history. Append to history again if status changes.
        """

        trend_indication = severity_code.trend(app.config['DEFAULT_SEVERITY'], alert.severity)
        if alert.status == status_code.UNKNOWN:
            status = status_code.status_from_severity(app.config['DEFAULT_SEVERITY'], alert.severity)
        else:
            status = alert.status

        now = datetime.datetime.utcnow()
        history = [{
            "id": alert.id,
            "event": alert.event,
            "severity": alert.severity,
            "value": alert.value,
            "type": "external",
            "text": alert.text,
            "updateTime": alert.create_time
        }]
        if status != alert.status:
            history.append({
                "event": alert.event,
                "status": status,
                "type": "auto",
                "text": "new alert status change",
                "id": alert.id,
                "updateTime": now
            })

        new = {
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
            "customer": alert.customer,
            "duplicateCount": 0,
            "repeat": False,
            "previousSeverity": app.config['DEFAULT_SEVERITY'],
            "trendIndication": trend_indication,
            "receiveTime": now,
            "lastReceiveId": alert.id,
            "lastReceiveTime": now,
            "history": history
        }

        LOG.debug('Insert new alert in database: %s', new)

        response = self._db.alerts.insert_one(new)
        if not response:
            return

        return AlertDocument(
            id=new['_id'],
            resource=new['resource'],
            event=new['event'],
            environment=new['environment'],
            severity=new['severity'],
            correlate=new['correlate'],
            status=new['status'],
            service=new['service'],
            group=new['group'],
            value=new['value'],
            text=new['text'],
            tags=new['tags'],
            attributes=new['attributes'],
            origin=new['origin'],
            event_type=new['type'],
            create_time=new['createTime'],
            timeout=new['timeout'],
            raw_data=new['rawData'],
            customer=new['customer'],
            duplicate_count=new['duplicateCount'],
            repeat=new['repeat'],
            previous_severity=new['previousSeverity'],
            trend_indication=new['trendIndication'],
            receive_time=new['receiveTime'],
            last_receive_id=new['lastReceiveId'],
            last_receive_time=new['lastReceiveTime'],
            history=list()
        )

    def get_alert(self, id, customer=None):

        if len(id) == 8:
            query = {'$or': [{'_id': {'$regex': '^' + id}}, {'lastReceiveId': {'$regex': '^' + id}}]}
        else:
            query = {'$or': [{'_id': id}, {'lastReceiveId': id}]}

        if customer:
            query['customer'] = customer

        response = self._db.alerts.find_one(query)
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
            customer=response.get('customer', None),
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

        event = self._db.alerts.find_one(query, projection={"event": 1, "_id": 0})['event']
        if not event:
            return False

        now = datetime.datetime.utcnow()
        update = {
            '$set': {"status": status},
            '$push': {
                "history": {
                    '$each': [{
                        "event": event,
                        "status": status,
                        "type": "external",
                        "text": text,
                        "id": id,
                        "updateTime": now
                    }],
                    '$slice': -abs(app.config['HISTORY_LIMIT'])
                }
            }
        }

        response = self._db.alerts.find_one_and_update(
            query,
            update=update,
            projection={"history": 0},
            return_document=ReturnDocument.AFTER
        )

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
            customer=response.get('customer', None),
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
        response = self._db.alerts.update_one({'_id': {'$regex': '^' + id}}, {'$addToSet': {"tags": {'$each': tags}}})

        return response.matched_count > 0

    def untag_alert(self, id, tags):
        """
        Remove tags from tag list.
        """
        response = self._db.alerts.update_one({'_id': {'$regex': '^' + id}}, {'$pullAll': {"tags": tags}})

        return response.matched_count > 0

    def update_attributes(self, id, attrs):
        """
        Set all attributes (including private attributes) and unset attributes by using a value of 'null'.
        """
        update = dict()
        set_value = {'attributes.' + k: v for k, v in attrs.items() if v is not None}
        if set_value:
            update['$set'] = set_value
        unset_value = {'attributes.' + k: v for k, v in attrs.items() if v is None}
        if unset_value:
            update['$unset'] = unset_value

        response = self._db.alerts.update_one({'_id': {'$regex': '^' + id}}, update=update)
        return response.matched_count > 0

    def delete_alert(self, id):

        response = self._db.alerts.delete_one({'_id': {'$regex': '^' + id}})

        return True if response.deleted_count == 1 else False

    def get_counts(self, query=None, fields=None, group=None):
        """
        Return counts grouped by severity or status.
        """
        fields = fields or {}

        pipeline = [
            {'$match': query},
            {'$project': fields},
            {'$group': {"_id": "$" + group, "count": {'$sum': 1}}}
        ]

        responses = self._db.alerts.aggregate(pipeline)

        counts = dict()
        for response in responses:
            counts[response['_id']] = response['count']

        return counts

    def get_topn_count(self, query=None, group=None, limit=10):

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

        responses = self._db.alerts.aggregate(pipeline)

        top = list()
        for response in responses:
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

    def get_topn_flapping(self, query=None, group=None, limit=10):

        if not group:
            group = "event"

        pipeline = [
            {'$match': query},
            {'$unwind': '$service'},
            {'$unwind': '$history'},
            {
                '$group': {
                    "_id": "$%s" % group,
                    "count": {'$sum': 1},
                    "duplicateCount": {'$max': "$duplicateCount"},
                    "environments": {'$addToSet': "$environment"},
                    "services": {'$addToSet': "$service"},
                    "resources": {'$addToSet': {"id": "$_id", "resource": "$resource"}}
                }
            },
            {'$sort': {"count": -1, "duplicateCount": -1}},
            {'$limit': limit}
        ]

        responses = self._db.alerts.aggregate(pipeline)

        top = list()
        for response in responses:
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

        responses = self._db.alerts.aggregate(pipeline)

        environments = list()
        for response in responses:
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

        responses = self._db.alerts.aggregate(pipeline)

        services = list()
        for response in responses:
            services.append(
                {
                    "environment": response['_id']['environment'],
                    "service": response['_id']['service'],
                    "count": response['count']
                }
            )
        return services

    def get_blackouts(self, query=None):

        now = datetime.datetime.utcnow()

        responses = self._db.blackouts.find(query)
        blackouts = list()
        for response in responses:
            response['id'] = response['_id']
            del response['_id']
            if response['startTime'] < now and response['endTime'] > now:
                response['status'] = "active"
                response['remaining'] = int((response['endTime'] - now).total_seconds())
            elif response['startTime'] > now:
                response['status'] = "pending"
                response['remaining'] = response['duration']
            elif response['endTime'] < now:
                response['status'] = "expired"
                response['remaining'] = 0
            blackouts.append(response)

        return blackouts

    def is_blackout_period(self, alert):
        
        if alert.severity in app.config.get('BLACKOUT_ACCEPT', []):
            return False

        now = datetime.datetime.utcnow()

        query = dict()
        query['startTime'] = {'$lte': now}
        query['endTime'] = {'$gt': now}

        query['environment'] = alert.environment
        query['$or'] = [
            {
                "resource": {'$exists': False},
                "service": {'$exists': False},
                "event": {'$exists': False},
                "group": {'$exists': False},
                "tags": {'$exists': False}
            },
            {
                "resource": alert.resource,
                "service": {'$exists': False},
                "event": {'$exists': False},
                "group": {'$exists': False},
                "tags": {'$exists': False}
            },
            {
                "resource": {'$exists': False},
                "service": {"$not": {"$elemMatch": {"$nin": alert.service}}},
                "event": {'$exists': False},
                "group": {'$exists': False},
                "tags": {'$exists': False}
            },
            {
                "resource": {'$exists': False},
                "service": {'$exists': False},
                "event": alert.event,
                "group": {'$exists': False},
                "tags": {'$exists': False}
            },
            {
                "resource": {'$exists': False},
                "service": {'$exists': False},
                "event": {'$exists': False},
                "group": alert.group,
                "tags": {'$exists': False}
            },
            {
                "resource": alert.resource,
                "service": {'$exists': False},
                "event": alert.event,
                "group": {'$exists': False},
                "tags": {'$exists': False}
            },
            {
                "resource": {'$exists': False},
                "service": {'$exists': False},
                "event": {'$exists': False},
                "group": {'$exists': False},
                "tags": {"$not": {"$elemMatch": {"$nin": alert.tags}}}
            }
        ]
        if self._db.blackouts.find_one(query):
            return True

        if app.config['CUSTOMER_VIEWS']:
            query['customer'] = alert.customer
            if self._db.blackouts.find_one(query):
                return True

        return False

    def create_blackout(self, environment, resource=None, service=None, event=None, group=None, tags=None, customer=None, start=None, end=None, duration=None):

        start = start or datetime.datetime.utcnow()
        if end:
            duration = int((end - start).total_seconds())
        else:
            duration = duration or app.config['BLACKOUT_DURATION']
            end = start + datetime.timedelta(seconds=duration)

        data = {
            "_id": str(uuid4()),
            "priority": 1,
            "environment": environment,
            "startTime": start,
            "endTime": end,
            "duration": duration
        }
        if resource and not event:
            data["priority"] = 2
            data["resource"] = resource
        elif service:
            data["priority"] = 3
            data["service"] = service
        elif event and not resource:
            data["priority"] = 4
            data["event"] = event
        elif group:
            data["priority"] = 5
            data["group"] = group
        elif resource and event:
            data["priority"] = 6
            data["resource"] = resource
            data["event"] = event
        elif tags:
            data["priority"] = 7
            data["tags"] = tags

        if app.config['CUSTOMER_VIEWS'] and customer:
            data["customer"] = customer

        return self._db.blackouts.insert_one(data).inserted_id

    def delete_blackout(self, id):

        response = self._db.blackouts.delete_one({"_id": id})

        return True if response.deleted_count == 1 else False

    def get_heartbeats(self, query=None):

        responses = self._db.heartbeats.find(query)

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
                    receive_time=response['receiveTime'],
                    customer=response.get('customer', None)
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
                "receiveTime": now,
                "customer": heartbeat.customer
            }
        }

        LOG.debug('Save heartbeat to database: %s', update)

        heartbeat_id = self._db.heartbeats.find_one({"origin": heartbeat.origin}, {})

        if heartbeat_id:
            response = self._db.heartbeats.find_one_and_update(
                {"origin": heartbeat.origin},
                update=update,
                upsert=True,
                return_document=ReturnDocument.AFTER
            )

            return HeartbeatDocument(
                id=response['_id'],
                origin=response['origin'],
                tags=response['tags'],
                event_type=response['type'],
                create_time=response['createTime'],
                timeout=response['timeout'],
                receive_time=response['receiveTime'],
                customer=response.get('customer', None)
            )
        else:
            update = update['$set']
            update["_id"] = heartbeat.id
            response = self._db.heartbeats.insert_one(update)

            return HeartbeatDocument(
                id=response.inserted_id,
                origin=update['origin'],
                tags=update['tags'],
                event_type=update['type'],
                create_time=update['createTime'],
                timeout=update['timeout'],
                receive_time=update['receiveTime'],
                customer=update.get('customer', None)
            )

    def get_heartbeat(self, id, customer=None):

        if len(id) == 8:
            query = {'$or': [{'_id': {'$regex': '^' + id}}, {'lastReceiveId': {'$regex': '^' + id}}]}
        else:
            query = {'$or': [{'_id': id}, {'lastReceiveId': id}]}

        if customer:
            query['customer'] = customer

        response = self._db.heartbeats.find_one(query)
        if not response:
            return

        return HeartbeatDocument(
            id=response['_id'],
            tags=response['tags'],
            origin=response['origin'],
            event_type=response['type'],
            create_time=response['createTime'],
            timeout=response['timeout'],
            receive_time=response['receiveTime'],
            customer=response.get('customer', None)
        )

    def delete_heartbeat(self, id):

        response = self._db.heartbeats.delete_one({'_id': {'$regex': '^' + id}})

        return True if response.deleted_count == 1 else False

    def get_user(self, id):

        user = self._db.users.find_one({"_id": id})

        if not user:
            return

        return {
            "id": user['_id'],
            "name": user['name'],
            "login": user['login'],
            "provider": user['provider'],
            "createTime": user['createTime'],
            "text": user['text']
        }

    def get_users(self, query=None, password=False):

        users = list()

        for user in self._db.users.find(query):
            login = user.get('login', None) or user.get('email', None)  # for backwards compatibility
            u = {
                "id": user['_id'],
                "name": user['name'],
                "login": login,
                "createTime": user['createTime'],
                "provider": user['provider'],
                "role": 'admin' if login in app.config.get('ADMIN_USERS') else 'user',
                "text": user.get('text', "")
            }
            if password:
                u['password'] = user.get('password', None)
            users.append(u)
        return users

    def is_user_valid(self, id=None, name=None, login=None):

        if id:
            return bool(self._db.users.find_one({"_id": id}))
        if name:
            return bool(self._db.users.find_one({"name": name}))
        if login:
            return bool(self._db.users.find_one({"login": login}))

    def update_user(self, id, name=None, login=None, password=None, provider=None, text=None, email_verified=None):

        if not self.is_user_valid(id=id):
            return

        data = {}
        if name:
            data['name'] = name
        if login:
            data['login'] = login
        if password:
            data['password'] = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(prefix=b'2a')).decode('utf-8')
        if provider:
            data['provider'] = provider
        if text:
            data['text'] = text
        if email_verified:
            data['email_verified'] = email_verified

        response = self._db.users.update_one({"_id": id}, {'$set': data})

        if response.matched_count > 0:
            return id
        else:
            return 

    def save_user(self, id, name, login, password=None, provider="", text="", email_verified=False):

        if self.is_user_valid(login=login):
            return

        data = {
            "_id": id,
            "name": name,
            "login": login,
            "createTime": datetime.datetime.utcnow(),
            "provider": provider,
            "text": text,
            "email_verified": email_verified
        }

        if password:
            data['password'] = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(prefix=b'2a')).decode('utf-8')

        return self._db.users.insert_one(data).inserted_id

    def reset_user_password(self, login, password):

        if not self.is_user_valid(login=login):
            return False

        self._db.users.update_one(
            {
                "login": login
            },
            {
                '$set': {"password": bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(prefix=b'2a')).decode('utf-8')}
            },
            upsert=True
        )
        return True

    def set_user_hash(self, login, hash):

        self._db.users.find_one_and_update(
            {'login': login},
            update={
                '$set': {'hash': hash, 'updateTime': datetime.datetime.utcnow()}
            },
            upsert=False,
        )

    def is_hash_valid(self, hash):

        user = self._db.users.find_one({"hash": hash})
        if user:
            return user['login']

    def validate_user(self, login):

        self._db.users.update_one(
            {"login": login},
            update={
                '$set': {'email_verified': True, "updateTime": datetime.datetime.utcnow()}
            },
            upsert=False
        )

    def is_email_verified(self, login):

        return self._db.users.find_one({'login': login}, projection={"email_verified": 1, "_id": 0}).get('email_verified', False)

    def delete_user(self, id):

        response = self._db.users.delete_one({"_id": id})

        return True if response.deleted_count == 1 else False

    def create_customer(self, customer, match):

        if self.get_customer_by_match(match):
            return

        data = {
            "_id": str(uuid4()),
            "customer": customer,
            "match": match
        }
        return self._db.customers.insert_one(data).inserted_id

    def get_customer_by_match(self, matches):

        if isinstance(matches, string_types):
            matches = [matches]

        def find_customer(match):
            response = self._db.customers.find_one({"match": match}, projection={"customer": 1, "_id": 0})
            if response:
                return response['customer']

        results = [find_customer(m) for m in matches]
        return next((r for r in results if r is not None), None)

    def get_customers(self, query=None):

        responses = self._db.customers.find(query)
        customers = list()
        for response in responses:
            customers.append(
                {
                    "id": response["_id"],
                    "customer": response["customer"],
                    "match": response.get("match", None) or response["reference"]
                }
            )
        return customers

    def delete_customer(self, customer):

        response = self._db.customers.delete_one({"customer": customer})
        return True if response.deleted_count == 1 else False

    def get_keys(self, query=None):

        responses = self._db.keys.find(query)
        keys = list()
        for response in responses:
            keys.append(
                {
                    "user": response["user"],
                    "key": response["key"],
                    "type": response.get("type", "read-write"),
                    "text": response["text"],
                    "expireTime": response["expireTime"],
                    "count": response["count"],
                    "lastUsedTime": response["lastUsedTime"],
                    "customer": response.get("customer", None)
                }
            )
        return keys

    def get_user_keys(self, login):

        if not self.is_user_valid(login=login):
            return

        return self.get_keys({"user": login})

    def is_key_valid(self, key):

        key_info = self._db.keys.find_one({"key": key})
        if key_info:
            if key_info['expireTime'] > datetime.datetime.utcnow():
                if 'type' not in key_info:
                    key_info['type'] = "read-write"
                return key_info
            else:
                return None
        else:
            return None

    def create_key(self, user, type='read-only', customer=None, text=None):

        try:
            random = str(os.urandom(32)).encode('utf-8')  # python 3
        except UnicodeDecodeError:
            random = str(os.urandom(32))  # python 2
        digest = hmac.new(app.config['SECRET_KEY'].encode('utf-8'), msg=random, digestmod=hashlib.sha256).digest()
        key = base64.urlsafe_b64encode(digest).decode('utf-8')[:40]

        data = {
            "user": user,
            "key": key,
            "type": type,  # read-only or read-write
            "text": text,
            "expireTime": datetime.datetime.utcnow() + datetime.timedelta(days=app.config.get('API_KEY_EXPIRE_DAYS', 30)),
            "count": 0,
            "lastUsedTime": None,
            "customer": customer
        }

        response = self._db.keys.insert_one(data)
        if not response:
            return None

        return key

    def update_key(self, key):

        self._db.keys.update_one(
            {
                "key": key
            },
            {
                '$set': {"lastUsedTime": datetime.datetime.utcnow()},
                '$inc': {"count": 1}
            },
            upsert=True
        )

    def delete_key(self, key):

        response = self._db.keys.delete_one({"key": key})
        return True if response.deleted_count == 1 else False

    def get_metrics(self):

        metrics = list()

        for stat in self._db.metrics.find({}, {"_id": 0}):
            metrics.append(stat)
        return metrics

    def disconnect(self):

        self._client.close()

        LOG.debug('Mongo connection closed.')
