
from datetime import datetime, timedelta

from flask import current_app
from pymongo import ASCENDING, TEXT, MongoClient, ReturnDocument
from pymongo.errors import ConnectionFailure

from alerta.database.base import Database
from alerta.exceptions import NoCustomerMatch

from .utils import Query

# See https://github.com/MongoEngine/flask-mongoengine/blob/master/flask_mongoengine/__init__.py
# See https://github.com/dcrosta/flask-pymongo/blob/master/flask_pymongo/__init__.py


class Backend(Database):

    def create_engine(self, app, uri, dbname=None):
        self.uri = uri
        self.dbname = dbname

        db = self.connect()
        self._create_indexes(db)

    def connect(self):
        self.client = MongoClient(self.uri)
        if self.dbname:
            return self.client[self.dbname]
        else:
            return self.client.get_default_database()

    @staticmethod
    def _create_indexes(db):
        db.alerts.create_index(
            [('environment', ASCENDING), ('customer', ASCENDING), ('resource', ASCENDING), ('event', ASCENDING)],
            unique=True
        )
        db.alerts.create_index([('$**', TEXT)])
        db.customers.create_index([('match', ASCENDING)], unique=True)
        db.heartbeats.create_index([('origin', ASCENDING), ('customer', ASCENDING)], unique=True)
        db.keys.create_index([('key', ASCENDING)], unique=True)
        db.perms.create_index([('match', ASCENDING)], unique=True)
        db.users.create_index([('email', ASCENDING)], unique=True)
        db.metrics.create_index([('group', ASCENDING), ('name', ASCENDING)], unique=True)

    @property
    def name(self):
        return self.get_db().name

    @property
    def version(self):
        return self.get_db().client.server_info()['version']

    @property
    def is_alive(self):
        try:
            self.get_db().client.admin.command('ismaster')
        except ConnectionFailure:
            return False
        return True

    def close(self):
        self.client.close()

    def destroy(self):
        db = self.connect()
        self.client.drop_database(db.name)

    # ALERTS

    def get_severity(self, alert):
        """
        Get severity of correlated alert. Used to determine previous severity.
        """
        query = {
            'environment': alert.environment,
            'resource': alert.resource,
            '$or': [
                {
                    'event': alert.event,
                    'severity': {'$ne': alert.severity}
                },
                {
                    'event': {'$ne': alert.event},
                    'correlate': alert.event
                }],
            'customer': alert.customer
        }
        r = self.get_db().alerts.find_one(query, projection={'severity': 1, '_id': 0})
        return r['severity'] if r else None

    def get_status(self, alert):
        """
        Get status of correlated or duplicate alert. Used to determine previous status.
        """
        query = {
            'environment': alert.environment,
            'resource': alert.resource,
            '$or': [
                {
                    'event': alert.event
                },
                {
                    'correlate': alert.event,
                }
            ],
            'customer': alert.customer
        }
        r = self.get_db().alerts.find_one(query, projection={'status': 1, '_id': 0})
        return r['status'] if r else None

    def get_status_and_value(self, alert):
        """
        Get status and value of correlated or duplicate alert. Used to determine if any have changed.
        """
        query = {
            'environment': alert.environment,
            'resource': alert.resource,
            '$or': [
                {
                    'event': alert.event
                },
                {
                    'correlate': alert.event,
                }
            ],
            'customer': alert.customer
        }
        r = self.get_db().alerts.find_one(query, projection={'status': 1, 'value': 1, '_id': 0})
        return (r['status'], r['value']) if r else (None, None)

    def is_duplicate(self, alert):
        query = {
            'environment': alert.environment,
            'resource': alert.resource,
            'event': alert.event,
            'severity': alert.severity,
            'customer': alert.customer
        }
        return bool(self.get_db().alerts.find_one(query))

    def is_correlated(self, alert):
        query = {
            'environment': alert.environment,
            'resource': alert.resource,
            '$or': [
                {
                    'event': alert.event,
                    'severity': {'$ne': alert.severity}
                },
                {
                    'event': {'$ne': alert.event},
                    'correlate': alert.event
                }],
            'customer': alert.customer
        }
        return bool(self.get_db().alerts.find_one(query))

    def is_flapping(self, alert, window=1800, count=2):
        """
        Return true if alert severity has changed more than X times in Y seconds
        """
        pipeline = [
            {'$match': {
                'environment': alert.environment,
                'resource': alert.resource,
                'event': alert.event,
                'customer': alert.customer
            }},
            {'$unwind': '$history'},
            {'$match': {
                'history.updateTime': {'$gt': datetime.utcnow() - timedelta(seconds=window)},
                'history.type': 'severity'
            }},
            {'$group': {'_id': '$history.type', 'count': {'$sum': 1}}}
        ]
        responses = self.get_db().alerts.aggregate(pipeline)
        for r in responses:
            if r['count'] > count:
                return True
        return False

    def dedup_alert(self, alert, history):
        """
        Update alert value, text and rawData, increment duplicate count and set repeat=True, and
        keep track of last receive id and time but don't append to history unless status changes.
        """
        query = {
            'environment': alert.environment,
            'resource': alert.resource,
            'event': alert.event,
            'severity': alert.severity,
            'customer': alert.customer
        }

        now = datetime.utcnow()
        update = {
            '$set': {
                'status': alert.status,
                'value': alert.value,
                'text': alert.text,
                'timeout': alert.timeout,
                'rawData': alert.raw_data,
                'repeat': True,
                'lastReceiveId': alert.id,
                'lastReceiveTime': now
            },
            '$addToSet': {'tags': {'$each': alert.tags}},
            '$inc': {'duplicateCount': 1}
        }

        # only update those attributes that are specifically defined
        attributes = {'attributes.' + k: v for k, v in alert.attributes.items()}
        update['$set'].update(attributes)

        if history:
            update['$push'] = {
                'history': {
                    '$each': [history.serialize],
                    '$slice': -abs(current_app.config['HISTORY_LIMIT'])
                }
            }

        return self.get_db().alerts.find_one_and_update(
            query,
            update=update,
            return_document=ReturnDocument.AFTER
        )

    def correlate_alert(self, alert, history):
        """
        Update alert key attributes, reset duplicate count and set repeat=False, keep track of last
        receive id and time, appending all to history. Append to history again if status changes.
        """
        query = {
            'environment': alert.environment,
            'resource': alert.resource,
            '$or': [
                {
                    'event': alert.event,
                    'severity': {'$ne': alert.severity}
                },
                {
                    'event': {'$ne': alert.event},
                    'correlate': alert.event
                }],
            'customer': alert.customer
        }

        update = {
            '$set': {
                'event': alert.event,
                'severity': alert.severity,
                'status': alert.status,
                'value': alert.value,
                'text': alert.text,
                'createTime': alert.create_time,
                'timeout': alert.timeout,
                'rawData': alert.raw_data,
                'duplicateCount': alert.duplicate_count,
                'repeat': alert.repeat,
                'previousSeverity': alert.previous_severity,
                'trendIndication': alert.trend_indication,
                'receiveTime': alert.receive_time,
                'lastReceiveId': alert.last_receive_id,
                'lastReceiveTime': alert.last_receive_time
            },
            '$addToSet': {'tags': {'$each': alert.tags}},
            '$push': {
                'history': {
                    '$each': [h.serialize for h in history],
                    '$slice': -abs(current_app.config['HISTORY_LIMIT'])
                }
            }
        }

        # only update those attributes that are specifically defined
        attributes = {'attributes.' + k: v for k, v in alert.attributes.items()}
        update['$set'].update(attributes)

        return self.get_db().alerts.find_one_and_update(
            query,
            update=update,
            return_document=ReturnDocument.AFTER
        )

    def create_alert(self, alert):
        data = {
            '_id': alert.id,
            'resource': alert.resource,
            'event': alert.event,
            'environment': alert.environment,
            'severity': alert.severity,
            'correlate': alert.correlate,
            'status': alert.status,
            'service': alert.service,
            'group': alert.group,
            'value': alert.value,
            'text': alert.text,
            'tags': alert.tags,
            'attributes': alert.attributes,
            'origin': alert.origin,
            'type': alert.event_type,
            'createTime': alert.create_time,
            'timeout': alert.timeout,
            'rawData': alert.raw_data,
            'customer': alert.customer,
            'duplicateCount': alert.duplicate_count,
            'repeat': alert.repeat,
            'previousSeverity': alert.previous_severity,
            'trendIndication': alert.trend_indication,
            'receiveTime': alert.receive_time,
            'lastReceiveId': alert.last_receive_id,
            'lastReceiveTime': alert.last_receive_time,
            'history': [h.serialize for h in alert.history]
        }
        if self.get_db().alerts.insert_one(data).inserted_id == alert.id:
            return data

    def set_alert(self, id, severity, status, tags, attributes, timeout, history=None):
        query = {'_id': {'$regex': '^' + id}}

        update = {
            '$set': {
                'severity': severity,
                'status': status,
                'timeout': timeout,
                'attributes': attributes
            },
            '$addToSet': {'tags': {'$each': tags}},
            '$push': {
                'history': {
                    '$each': [history.serialize],
                    '$slice': -abs(current_app.config['HISTORY_LIMIT'])
                }
            }
        }

        return self.get_db().alerts.find_one_and_update(
            query,
            update=update,
            return_document=ReturnDocument.AFTER
        )

    def get_alert(self, id, customers=None):
        if len(id) == 8:
            query = {'$or': [{'_id': {'$regex': '^' + id}}, {'lastReceiveId': {'$regex': '^' + id}}]}
        else:
            query = {'$or': [{'_id': id}, {'lastReceiveId': id}]}

        if customers:
            query['customer'] = {'$in': customers}

        return self.get_db().alerts.find_one(query)

    # STATUS, TAGS, ATTRIBUTES

    def set_status(self, id, status, timeout, history=None):
        """
        Set status and update history.
        """
        query = {'_id': {'$regex': '^' + id}}

        update = {
            '$set': {'status': status, 'timeout': timeout},
            '$push': {
                'history': {
                    '$each': [history.serialize],
                    '$slice': -abs(current_app.config['HISTORY_LIMIT'])
                }
            }
        }
        return self.get_db().alerts.find_one_and_update(
            query,
            update=update,
            projection={'history': 0},
            return_document=ReturnDocument.AFTER
        )

    def set_severity_and_status(self, id, severity, status, timeout, history=None):
        """
        Set severity and status and update history.
        """
        query = {'_id': {'$regex': '^' + id}}

        update = {
            '$set': {'severity': severity, 'status': status, 'timeout': timeout},
            '$push': {
                'history': {
                    '$each': [history.serialize],
                    '$slice': -abs(current_app.config['HISTORY_LIMIT'])
                }
            }
        }
        return self.get_db().alerts.find_one_and_update(
            query,
            update=update,
            projection={'history': 0},
            return_document=ReturnDocument.AFTER
        )

    def tag_alert(self, id, tags):
        """
        Append tags to tag list. Don't add same tag more than once.
        """
        response = self.get_db().alerts.update_one(
            {'_id': {'$regex': '^' + id}}, {'$addToSet': {'tags': {'$each': tags}}})
        return response.matched_count > 0

    def untag_alert(self, id, tags):
        """
        Remove tags from tag list.
        """
        response = self.get_db().alerts.update_one({'_id': {'$regex': '^' + id}}, {'$pullAll': {'tags': tags}})
        return response.matched_count > 0

    def update_attributes(self, id, old_attrs, new_attrs):
        """
        Set all attributes (including private attributes) and unset attributes by using a value of 'null'.
        """
        update = dict()
        set_value = {'attributes.' + k: v for k, v in new_attrs.items() if v is not None}
        if set_value:
            update['$set'] = set_value
        unset_value = {'attributes.' + k: v for k, v in new_attrs.items() if v is None}
        if unset_value:
            update['$unset'] = unset_value

        response = self.get_db().alerts.update_one({'_id': {'$regex': '^' + id}}, update=update)
        return response.matched_count > 0

    def delete_alert(self, id):
        response = self.get_db().alerts.delete_one({'_id': {'$regex': '^' + id}})
        return True if response.deleted_count == 1 else False

    # BULK

    def tag_alerts(self, query=None, tags=None):
        query = query or Query()
        updated = list(self.get_db().alerts.find(query.where, projection={'_id': 1}))
        response = self.get_db().alerts.update(query.where, {'$addToSet': {'tags': {'$each': tags}}})
        return updated if response['n'] else []

    def untag_alerts(self, query=None, tags=None):
        query = query or Query()
        updated = list(self.get_db().alerts.find(query.where, projection={'_id': 1}))
        response = self.get_db().alerts.update(query.where, {'$pullAll': {'tags': tags}})
        return updated if response['n'] else []

    def update_attributes_by_query(self, query=None, attributes=None):
        query = query or Query()
        update = dict()
        set_value = {'attributes.' + k: v for k, v in attributes.items() if v is not None}
        if set_value:
            update['$set'] = set_value
        unset_value = {'attributes.' + k: v for k, v in attributes.items() if v is None}
        if unset_value:
            update['$unset'] = unset_value

        updated = list(self.get_db().alerts.find(query.where, projection={'_id': 1}))
        response = self.get_db().alerts.update_many(query.where, update=update)
        return updated if response.matched_count > 0 else []

    def delete_alerts(self, query=None):
        query = query or Query()
        deleted = list(self.get_db().alerts.find(query.where, projection={'_id': 1}))
        response = self.get_db().alerts.remove(query.where)
        return deleted if response['n'] else []

    # SEARCH & HISTORY

    def get_alerts(self, query=None, page=None, page_size=None):
        query = query or Query()
        return self.get_db().alerts.find(query.where, sort=query.sort).skip((page - 1) * page_size).limit(page_size)

    def get_history(self, query=None, page=None, page_size=None):
        query = query or Query()
        fields = {
            'resource': 1,
            'event': 1,
            'environment': 1,
            'customer': 1,
            'service': 1,
            'group': 1,
            'tags': 1,
            'attributes': 1,
            'origin': 1,
            'type': 1,
            'history': 1
        }

        pipeline = [
            {'$unwind': '$history'},
            {'$match': query.where},
            {'$project': fields},
            {'$sort': {'history.updateTime': -1}},
            {'$skip': (page - 1) * page_size},
            {'$limit': page_size},
        ]

        responses = self.get_db().alerts.aggregate(pipeline)

        history = list()
        for response in responses:
            history.append(
                {
                    'id': response['history']['id'],
                    'resource': response['resource'],
                    'event': response['history']['event'],
                    'environment': response['environment'],
                    'severity': response['history']['severity'],
                    'service': response['service'],
                    'status': response['history']['status'],
                    'group': response['group'],
                    'value': response['history']['value'],
                    'text': response['history']['text'],
                    'tags': response['tags'],
                    'attributes': response['attributes'],
                    'origin': response['origin'],
                    'updateTime': response['history']['updateTime'],
                    'type': response['history'].get('type', 'unknown'),
                    'customer': response.get('customer', None)
                }
            )
        return history

    # COUNTS

    def get_count(self, query=None):
        """
        Return total number of alerts that meet the query filter.
        """
        query = query or Query()
        return self.get_db().alerts.find(query.where).count()

    def get_counts(self, query=None, group=None):
        query = query or Query()
        if group is None:
            raise ValueError('Must define a group')
        pipeline = [
            {'$match': query.where},
            {'$project': {group: 1}},
            {'$group': {'_id': '$' + group, 'count': {'$sum': 1}}}
        ]
        responses = self.get_db().alerts.aggregate(pipeline)

        counts = dict()
        for response in responses:
            counts[response['_id']] = response['count']
        return counts

    def get_counts_by_severity(self, query=None):
        query = query or Query()
        return self.get_counts(query, group='severity')

    def get_counts_by_status(self, query=None):
        query = query or Query()
        return self.get_counts(query, group='status')

    def get_topn_count(self, query=None, group='event', topn=100):
        query = query or Query()
        pipeline = [
            {'$match': query.where},
            {'$unwind': '$service'},
            {
                '$group': {
                    '_id': '$%s' % group,
                    'count': {'$sum': 1},
                    'duplicateCount': {'$sum': '$duplicateCount'},
                    'environments': {'$addToSet': '$environment'},
                    'services': {'$addToSet': '$service'},
                    'resources': {'$addToSet': {'id': '$_id', 'resource': '$resource'}}
                }
            },
            {'$sort': {'count': -1, 'duplicateCount': -1}},
            {'$limit': topn}
        ]

        responses = self.get_db().alerts.aggregate(pipeline)

        top = list()
        for response in responses:
            top.append(
                {
                    '%s' % group: response['_id'],
                    'environments': response['environments'],
                    'services': response['services'],
                    'resources': response['resources'],
                    'count': response['count'],
                    'duplicateCount': response['duplicateCount']
                }
            )
        return top

    def get_topn_flapping(self, query=None, group='event', topn=100):
        query = query or Query()
        pipeline = [
            {'$match': query.where},
            {'$unwind': '$service'},
            {'$unwind': '$history'},
            {'$match': {'history.type': 'severity'}},
            {
                '$group': {
                    '_id': '$%s' % group,
                    'count': {'$sum': 1},
                    'duplicateCount': {'$max': '$duplicateCount'},
                    'environments': {'$addToSet': '$environment'},
                    'services': {'$addToSet': '$service'},
                    'resources': {'$addToSet': {'id': '$_id', 'resource': '$resource'}}
                }
            },
            {'$sort': {'count': -1, 'duplicateCount': -1}},
            {'$limit': topn}
        ]

        responses = self.get_db().alerts.aggregate(pipeline)

        top = list()
        for response in responses:
            top.append(
                {
                    '%s' % group: response['_id'],
                    'environments': response['environments'],
                    'services': response['services'],
                    'resources': response['resources'],
                    'count': response['count'],
                    'duplicateCount': response['duplicateCount']
                }
            )
        return top

    def get_topn_standing(self, query=None, group='event', topn=100):
        query = query or Query()
        pipeline = [
            {'$match': query.where},
            {'$unwind': '$service'},
            {
                '$group': {
                    '_id': '$%s' % group,
                    'count': {'$sum': 1},
                    'duplicateCount': {'$sum': '$duplicateCount'},
                    'lifeTime': {'$sum': {'$subtract': ['$lastReceiveTime', '$createTime']}},
                    'environments': {'$addToSet': '$environment'},
                    'services': {'$addToSet': '$service'},
                    'resources': {'$addToSet': {'id': '$_id', 'resource': '$resource'}}
                }
            },
            {'$sort': {'lifeTime': -1, 'duplicateCount': -1}},
            {'$limit': topn}
        ]

        responses = self.get_db().alerts.aggregate(pipeline)
        top = list()
        for response in responses:
            top.append(
                {
                    '%s' % group: response['_id'],
                    'environments': response['environments'],
                    'services': response['services'],
                    'resources': response['resources'],
                    'count': response['count'],
                    'duplicateCount': response['duplicateCount']
                }
            )
        return top

    # ENVIRONMENTS

    def get_environments(self, query=None, topn=1000):
        query = query or Query()
        pipeline = [
            {'$match': query.where},
            {'$project': {'environment': 1}},
            {'$group': {'_id': '$environment', 'count': {'$sum': 1}}},
            {'$limit': topn}
        ]
        responses = self.get_db().alerts.aggregate(pipeline)

        environments = list()
        for response in responses:
            environments.append(
                {
                    'environment': response['_id'],
                    'count': response['count']
                }
            )
        return environments

    # SERVICES

    def get_services(self, query=None, topn=1000):
        query = query or Query()
        pipeline = [
            {'$unwind': '$service'},
            {'$match': query.where},
            {'$project': {'environment': 1, 'service': 1}},
            {'$group': {'_id': {'environment': '$environment', 'service': '$service'}, 'count': {'$sum': 1}}},
            {'$limit': topn}
        ]
        responses = self.get_db().alerts.aggregate(pipeline)

        services = list()
        for response in responses:
            services.append(
                {
                    'environment': response['_id']['environment'],
                    'service': response['_id']['service'],
                    'count': response['count']
                }
            )
        return services

    # TAGS

    def get_tags(self, query=None, topn=1000):
        query = query or Query()
        pipeline = [
            {'$unwind': '$tags'},
            {'$match': query.where},
            {'$project': {'environment': 1, 'tags': 1}},
            {'$limit': topn},
            {'$group': {'_id': {'environment': '$environment', 'tag': '$tags'}, 'count': {'$sum': 1}}}
        ]
        responses = self.get_db().alerts.aggregate(pipeline)

        tags = list()
        for response in responses:
            tags.append(
                {
                    'environment': response['_id']['environment'],
                    'tag': response['_id']['tag'],
                    'count': response['count']
                }
            )
        return tags

    # BLACKOUTS

    def create_blackout(self, blackout):
        data = {
            '_id': blackout.id,
            'priority': blackout.priority,
            'environment': blackout.environment,
            'startTime': blackout.start_time,
            'endTime': blackout.end_time,
            'duration': blackout.duration,
            'user': blackout.user,
            'createTime': blackout.create_time,
            'text': blackout.text,
        }
        if blackout.service:
            data['service'] = blackout.service
        if blackout.resource:
            data['resource'] = blackout.resource
        if blackout.event:
            data['event'] = blackout.event
        if blackout.group:
            data['group'] = blackout.group
        if blackout.tags:
            data['tags'] = blackout.tags
        if blackout.customer:
            data['customer'] = blackout.customer

        if self.get_db().blackouts.insert_one(data).inserted_id == blackout.id:
            return data

    def get_blackout(self, id, customer=None):
        query = {'_id': id}
        if customer:
            query['customer'] = customer
        return self.get_db().blackouts.find_one(query)

    def get_blackouts(self, query=None):
        query = query or Query()
        return self.get_db().blackouts.find(query.where)

    def is_blackout_period(self, alert):
        now = datetime.utcnow()

        query = dict()
        query['startTime'] = {'$lte': now}
        query['endTime'] = {'$gt': now}

        query['environment'] = alert.environment
        query['$and'] = [{'$or': [
            {
                'resource': {'$exists': False},
                'service': {'$exists': False},
                'event': {'$exists': False},
                'group': {'$exists': False},
                'tags': {'$exists': False}
            },
            {
                'resource': {'$exists': False},
                'service': {'$exists': False},
                'event': {'$exists': False},
                'group': {'$exists': False},
                'tags': {'$not': {'$elemMatch': {'$nin': alert.tags}}}
            },
            {
                'resource': {'$exists': False},
                'service': {'$exists': False},
                'event': {'$exists': False},
                'group': alert.group,
                'tags': {'$exists': False}
            },
            {
                'resource': {'$exists': False},
                'service': {'$exists': False},
                'event': {'$exists': False},
                'group': alert.group,
                'tags': {'$not': {'$elemMatch': {'$nin': alert.tags}}}
            },
            {
                'resource': {'$exists': False},
                'service': {'$exists': False},
                'event': alert.event,
                'group': {'$exists': False},
                'tags': {'$exists': False}
            },
            {
                'resource': {'$exists': False},
                'service': {'$exists': False},
                'event': alert.event,
                'group': {'$exists': False},
                'tags': {'$not': {'$elemMatch': {'$nin': alert.tags}}}
            },
            {
                'resource': {'$exists': False},
                'service': {'$exists': False},
                'event': alert.event,
                'group': alert.group,
                'tags': {'$exists': False}
            },
            {
                'resource': {'$exists': False},
                'service': {'$exists': False},
                'event': alert.event,
                'group': alert.group,
                'tags': {'$not': {'$elemMatch': {'$nin': alert.tags}}}
            },
            {
                'resource': {'$exists': False},
                'service': {'$not': {'$elemMatch': {'$nin': alert.service}}},
                'event': {'$exists': False},
                'group': {'$exists': False},
                'tags': {'$exists': False}
            },
            {
                'resource': {'$exists': False},
                'service': {'$not': {'$elemMatch': {'$nin': alert.service}}},
                'event': {'$exists': False},
                'group': {'$exists': False},
                'tags': {'$not': {'$elemMatch': {'$nin': alert.tags}}}
            },
            {
                'resource': {'$exists': False},
                'service': {'$not': {'$elemMatch': {'$nin': alert.service}}},
                'event': {'$exists': False},
                'group': alert.group,
                'tags': {'$exists': False}
            },
            {
                'resource': {'$exists': False},
                'service': {'$not': {'$elemMatch': {'$nin': alert.service}}},
                'event': {'$exists': False},
                'group': alert.group,
                'tags': {'$not': {'$elemMatch': {'$nin': alert.tags}}}
            },
            {
                'resource': {'$exists': False},
                'service': {'$not': {'$elemMatch': {'$nin': alert.service}}},
                'event': alert.event,
                'group': {'$exists': False},
                'tags': {'$exists': False}
            },
            {
                'resource': {'$exists': False},
                'service': {'$not': {'$elemMatch': {'$nin': alert.service}}},
                'event': alert.event,
                'group': {'$exists': False},
                'tags': {'$not': {'$elemMatch': {'$nin': alert.tags}}}
            },
            {
                'resource': {'$exists': False},
                'service': {'$not': {'$elemMatch': {'$nin': alert.service}}},
                'event': alert.event,
                'group': alert.group,
                'tags': {'$exists': False}
            },
            {
                'resource': {'$exists': False},
                'service': {'$not': {'$elemMatch': {'$nin': alert.service}}},
                'event': alert.event,
                'group': alert.group,
                'tags': {'$not': {'$elemMatch': {'$nin': alert.tags}}}
            },
            {
                'resource': alert.resource,
                'service': {'$exists': False},
                'event': {'$exists': False},
                'group': {'$exists': False},
                'tags': {'$exists': False}
            },
            {
                'resource': alert.resource,
                'service': {'$exists': False},
                'event': {'$exists': False},
                'group': {'$exists': False},
                'tags': {'$not': {'$elemMatch': {'$nin': alert.tags}}}
            },
            {
                'resource': alert.resource,
                'service': {'$exists': False},
                'event': {'$exists': False},
                'group': alert.group,
                'tags': {'$exists': False}
            },
            {
                'resource': alert.resource,
                'service': {'$exists': False},
                'event': {'$exists': False},
                'group': alert.group,
                'tags': {'$not': {'$elemMatch': {'$nin': alert.tags}}}
            },
            {
                'resource': alert.resource,
                'service': {'$exists': False},
                'event': alert.event,
                'group': {'$exists': False},
                'tags': {'$exists': False}
            },
            {
                'resource': alert.resource,
                'service': {'$exists': False},
                'event': alert.event,
                'group': {'$exists': False},
                'tags': {'$not': {'$elemMatch': {'$nin': alert.tags}}}
            },
            {
                'resource': alert.resource,
                'service': {'$exists': False},
                'event': alert.event,
                'group': alert.group,
                'tags': {'$exists': False}
            },
            {
                'resource': alert.resource,
                'service': {'$exists': False},
                'event': alert.event,
                'group': alert.group,
                'tags': {'$not': {'$elemMatch': {'$nin': alert.tags}}}
            },
            {
                'resource': alert.resource,
                'service': {'$not': {'$elemMatch': {'$nin': alert.service}}},
                'event': {'$exists': False},
                'group': {'$exists': False},
                'tags': {'$exists': False}
            },
            {
                'resource': alert.resource,
                'service': {'$not': {'$elemMatch': {'$nin': alert.service}}},
                'event': {'$exists': False},
                'group': {'$exists': False},
                'tags': {'$not': {'$elemMatch': {'$nin': alert.tags}}}
            },
            {
                'resource': alert.resource,
                'service': {'$not': {'$elemMatch': {'$nin': alert.service}}},
                'event': {'$exists': False},
                'group': alert.group,
                'tags': {'$exists': False}
            },
            {
                'resource': alert.resource,
                'service': {'$not': {'$elemMatch': {'$nin': alert.service}}},
                'event': {'$exists': False},
                'group': alert.group,
                'tags': {'$not': {'$elemMatch': {'$nin': alert.tags}}}
            },
            {
                'resource': alert.resource,
                'service': {'$not': {'$elemMatch': {'$nin': alert.service}}},
                'event': alert.event,
                'group': {'$exists': False},
                'tags': {'$exists': False}
            },
            {
                'resource': alert.resource,
                'service': {'$not': {'$elemMatch': {'$nin': alert.service}}},
                'event': alert.event,
                'group': {'$exists': False},
                'tags': {'$not': {'$elemMatch': {'$nin': alert.tags}}}
            },
            {
                'resource': alert.resource,
                'service': {'$not': {'$elemMatch': {'$nin': alert.service}}},
                'event': alert.event,
                'group': alert.group,
                'tags': {'$exists': False}
            },
            {
                'resource': alert.resource,
                'service': {'$not': {'$elemMatch': {'$nin': alert.service}}},
                'event': alert.event,
                'group': alert.group,
                'tags': {'$not': {'$elemMatch': {'$nin': alert.tags}}}
            }
        ]}]

        if current_app.config['CUSTOMER_VIEWS']:
            query['$and'].append({'$or': [{'customer': None}, {'customer': alert.customer}]})
        if self.get_db().blackouts.find_one(query):
            return True
        return False

    def delete_blackout(self, id):
        response = self.get_db().blackouts.delete_one({'_id': id})
        return True if response.deleted_count == 1 else False

    # HEARTBEATS

    def upsert_heartbeat(self, heartbeat):
        return self.get_db().heartbeats.find_one_and_update(
            {
                'origin': heartbeat.origin,
                'customer': heartbeat.customer
            },
            {
                '$setOnInsert': {
                    '_id': heartbeat.id
                },
                '$set': {
                    'origin': heartbeat.origin,
                    'tags': heartbeat.tags,
                    'type': heartbeat.event_type,
                    'createTime': heartbeat.create_time,
                    'timeout': heartbeat.timeout,
                    'receiveTime': heartbeat.receive_time,
                    'customer': heartbeat.customer
                }
            },
            upsert=True,
            return_document=ReturnDocument.AFTER
        )

    def get_heartbeat(self, id, customers=None):
        if len(id) == 8:
            query = {'_id': {'$regex': '^' + id}}
        else:
            query = {'_id': id}

        if customers:
            query['customer'] = {'$in': customers}

        return self.get_db().heartbeats.find_one(query)

    def get_heartbeats(self, query=None):
        query = query or Query()
        return self.get_db().heartbeats.find(query.where)

    def delete_heartbeat(self, id):
        response = self.get_db().heartbeats.delete_one({'_id': {'$regex': '^' + id}})
        return True if response.deleted_count == 1 else False

    # API KEYS

    # save
    def create_key(self, key):
        data = {
            '_id': key.id,
            'key': key.key,
            'user': key.user,
            'scopes': key.scopes,
            'text': key.text,
            'expireTime': key.expire_time,
            'count': key.count,
            'lastUsedTime': key.last_used_time
        }
        if key.customer:
            data['customer'] = key.customer

        if self.get_db().keys.insert_one(data).inserted_id == key.id:
            return data

    # get
    def get_key(self, key):
        query = {'$or': [{'key': key}, {'_id': key}]}
        return self.get_db().keys.find_one(query)

    # list
    def get_keys(self, query=None):
        query = query or Query()
        return self.get_db().keys.find(query.where)

    # update
    def update_key_last_used(self, key):
        return self.get_db().keys.update_one(
            {'$or': [{'key': key}, {'_id': key}]},
            {
                '$set': {'lastUsedTime': datetime.utcnow()},
                '$inc': {'count': 1}
            }
        ).matched_count == 1

    # delete
    def delete_key(self, key):
        query = {'$or': [{'key': key}, {'_id': key}]}
        response = self.get_db().keys.delete_one(query)
        return True if response.deleted_count == 1 else False

    # USERS

    def create_user(self, user):
        data = {
            '_id': user.id,
            'name': user.name,
            'email': user.email,
            'password': user.password,
            'status': user.status,
            'roles': user.roles,
            'attributes': user.attributes,
            'createTime': user.create_time,
            'lastLogin': user.last_login,
            'text': user.text,
            'updateTime': user.update_time,
            'email_verified': user.email_verified
        }
        if self.get_db().users.insert_one(data).inserted_id == user.id:
            return data

    # get
    def get_user(self, id):
        query = {'_id': id}
        return self.get_db().users.find_one(query)

    # list
    def get_users(self, query=None):
        query = query or Query()
        return self.get_db().users.find(query.where)

    def get_user_by_email(self, email):
        if not email:
            return
        query = {'$or': [{'email': email}, {'login': email}]}
        return self.get_db().users.find_one(query)

    def get_user_by_hash(self, hash):
        query = {'hash': hash}
        return self.get_db().users.find_one(query)

    def update_last_login(self, id):
        return self.get_db().users.update_one(
            {'_id': id},
            update={'$set': {'lastLogin': datetime.utcnow()}}
        ).matched_count == 1

    def update_user(self, id, **kwargs):
        kwargs['updateTime'] = datetime.utcnow()
        return self.get_db().users.find_one_and_update(
            {'_id': id},
            update={'$set': kwargs},
            return_document=ReturnDocument.AFTER
        )

    def update_user_attributes(self, id, old_attrs, new_attrs):
        update = dict()
        set_value = {'attributes.' + k: v for k, v in new_attrs.items() if v is not None}
        if set_value:
            update['$set'] = set_value
        unset_value = {'attributes.' + k: v for k, v in new_attrs.items() if v is None}
        if unset_value:
            update['$unset'] = unset_value

        response = self.get_db().users.update_one({'_id': {'$regex': '^' + id}}, update=update)
        return response.matched_count > 0

    def delete_user(self, id):
        response = self.get_db().users.delete_one({'_id': id})
        return True if response.deleted_count == 1 else False

    def set_email_hash(self, id, hash):
        return self.get_db().users.update_one(
            {'_id': id},
            update={'$set': {'hash': hash, 'updateTime': datetime.utcnow()}}
        ).matched_count == 1

    # PERMISSIONS

    def create_perm(self, perm):
        data = {
            '_id': perm.id,
            'match': perm.match,
            'scopes': perm.scopes
        }
        if self.get_db().perms.insert_one(data).inserted_id == perm.id:
            return data

    def get_perm(self, id):
        query = {'_id': id}
        return self.get_db().perms.find_one(query)

    def get_perms(self, query=None):
        query = query or Query()
        return self.get_db().perms.find(query.where)

    def delete_perm(self, id):
        response = self.get_db().perms.delete_one({'_id': id})
        return True if response.deleted_count == 1 else False

    def get_scopes_by_match(self, login, matches):
        if login in current_app.config['ADMIN_USERS']:
            return ['admin', 'read', 'write']

        scopes = list()
        for match in matches:
            response = self.get_db().perms.find_one({'match': match}, projection={'scopes': 1, '_id': 0})
            if response:
                scopes.extend(response['scopes'])
        return set(scopes) or current_app.config['USER_DEFAULT_SCOPES']

    # CUSTOMERS

    def create_customer(self, customer):
        data = {
            '_id': customer.id,
            'match': customer.match,
            'customer': customer.customer
        }
        if self.get_db().customers.insert_one(data).inserted_id == customer.id:
            return data

    def get_customer(self, id):
        query = {'_id': id}
        return self.get_db().customers.find_one(query)

    def get_customers(self, query=None):
        query = query or Query()
        return self.get_db().customers.find(query.where)

    def delete_customer(self, id):
        response = self.get_db().customers.delete_one({'_id': id})
        return True if response.deleted_count == 1 else False

    def get_customers_by_match(self, login, matches):
        if login in current_app.config['ADMIN_USERS']:
            return '*'  # all customers

        customers = []
        for match in [login] + matches:
            response = self.get_db().customers.find_one({'match': match}, projection={'customer': 1, '_id': 0})
            if response:
                customers.append(response['customer'])

        if customers:
            if '*' in customers:
                return '*'  # all customers

            return customers

        raise NoCustomerMatch("No customer lookup configured for user '{}' or '{}'".format(login, ','.join(matches)))

    # METRICS

    def get_metrics(self, type=None):
        query = {'type': type} if type else {}
        return list(self.get_db().metrics.find(query, {'_id': 0}))

    def set_gauge(self, gauge):

        return self.get_db().metrics.find_one_and_update(
            {
                'group': gauge.group,
                'name': gauge.name
            },
            {
                '$set': {
                    'group': gauge.group,
                    'name': gauge.name,
                    'title': gauge.title,
                    'description': gauge.description,
                    'value': gauge.value,
                    'type': 'gauge'
                }
            },
            upsert=True,
            return_document=ReturnDocument.AFTER
        )['value']

    def inc_counter(self, counter):

        return self.get_db().metrics.find_one_and_update(
            {
                'group': counter.group,
                'name': counter.name
            },
            {
                '$set': {
                    'group': counter.group,
                    'name': counter.name,
                    'title': counter.title,
                    'description': counter.description,
                    'type': 'counter'
                },
                '$inc': {'count': counter.count}
            },
            upsert=True,
            return_document=ReturnDocument.AFTER
        )['count']

    def update_timer(self, timer):
        return self.get_db().metrics.find_one_and_update(
            {
                'group': timer.group,
                'name': timer.name
            },
            {
                '$set': {
                    'group': timer.group,
                    'name': timer.name,
                    'title': timer.title,
                    'description': timer.description,
                    'type': 'timer'
                },
                '$inc': {'count': timer.count, 'totalTime': timer.total_time}
            },
            upsert=True,
            return_document=ReturnDocument.AFTER
        )

    # HOUSEKEEPING

    def housekeeping(self, expired_threshold, info_threshold):
        # delete 'closed' or 'expired' alerts older than "expired_threshold" hours
        # and 'informational' alerts older than "info_threshold" hours
        expired_hours_ago = datetime.utcnow() - timedelta(hours=expired_threshold)
        self.get_db().alerts.remove(
            {'status': {'$in': ['closed', 'expired']}, 'lastReceiveTime': {'$lt': expired_hours_ago}})

        info_hours_ago = datetime.utcnow() - timedelta(hours=info_threshold)
        self.get_db().alerts.remove({'severity': 'informational', 'lastReceiveTime': {'$lt': info_hours_ago}})

        # get list of alerts to be newly expired
        pipeline = [
            {'$project': {
                'event': 1, 'status': 1, 'lastReceiveId': 1, 'timeout': 1,
                'expireTime': {'$add': ['$lastReceiveTime', {'$multiply': ['$timeout', 1000]}]}}
             },
            {'$match': {'status': {'$nin': ['expired', 'shelved']}, 'expireTime': {'$lt': datetime.utcnow()}, 'timeout': {
                '$ne': 0}}}
        ]
        expired = [(r['_id'], r['event'], r['lastReceiveId']) for r in self.get_db().alerts.aggregate(pipeline)]

        # get list of alerts to be unshelved
        pipeline = [
            {'$match': {'status': 'shelved'}},
            {'$unwind': '$history'},
            {'$match': {
                'history.type': 'action',
                'history.status': 'shelved'
            }},
            {'$sort': {'history.updateTime': -1}},
            {'$group': {
                '_id': '$_id',
                'event': {'$first': '$event'},
                'lastReceiveId': {'$first': '$lastReceiveId'},
                'updateTime': {'$first': '$history.updateTime'},
                'timeout': {'$first': '$timeout'}
            }},
            {'$project': {
                'event': 1,
                'lastReceiveId': 1,
                'expireTime': {'$add': ['$updateTime', {'$multiply': ['$timeout', 1000]}]}
            }},
            {'$match': {'expireTime': {'$lt': datetime.utcnow()}, 'timeout': {'$ne': 0}}}
        ]
        unshelved = [(r['_id'], r['event'], r['lastReceiveId']) for r in self.get_db().alerts.aggregate(pipeline)]

        return (expired, unshelved)
