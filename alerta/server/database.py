import sys
import datetime
import pytz

import pymongo

from alerta.common import log as logging
from alerta.common import config
from alerta.alert import Alert

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

        # TODO(nsatterl): problems running under pymongo 2.1.1
        # if self.conn.alive():
        #     LOG.info('Connected to MongoDB server %s:%s', CONF.mongo_host, CONF.mongo_port)
        #     LOG.debug('MongoDB %s, databases available: %s', self.conn.server_info()['version'], ', '.join(self.conn.database_names()))

        self.create_indexes()

    def create_indexes(self):

        self.db.alerts.create_index([('environment', pymongo.ASCENDING), ('resource', pymongo.ASCENDING),
                                     ('event', pymongo.ASCENDING), ('severity', pymongo.ASCENDING)])
        self.db.alerts.create_index([('_id', pymongo.ASCENDING), ('environment', pymongo.ASCENDING),
                                     ('resource', pymongo.ASCENDING), ('event', pymongo.ASCENDING)])
        self.db.alerts.create_index([('status', pymongo.ASCENDING), ('expireTime', pymongo.ASCENDING)])

    def is_duplicate(self, environment, resource, event, severity=None):

        if severity:
            found = self.db.alerts.find_one({"environment": environment, "resource": resource, "event": event, "severity": severity})
        else:
            found = self.db.alerts.find_one({"environment": environment, "resource": resource, "event": event})

        return found is not None

    def is_correlated(self, environment, resource, event):

        found = self.db.alerts.find_one({"environment": environment, "resource": resource,
                                         '$or': [{"event": event}, {"correlatedEvents": event}]})
        return found is not None

    def get_severity(self, environment, resource, event):

        return self.db.alerts.find_one({"environment": environment, "resource": resource,
                                        '$or': [{"event": event}, {"correlatedEvents": event}]},
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

    def update_alert(self, alertid=None, environment=None, resource=None, event=None, update=None):

        if alertid:
            query = {'_id': {'$regex': '^' + alertid}}
        else:
            query = {"environment": environment, "resource": resource,
                     '$or': [{"event": event}, {"correlatedEvents": event}]}

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

    def partial_update_alert(self, alertid=None, environment=None, resource=None, event=None, update=None):

        if alertid:
            query = {'_id': {'$regex': '^' + alertid}}
        else:
            query = {"environment": environment, "resource": resource,
                     '$or': [{"event": event}, {"correlatedEvents": event}]}

        response = self.db.alerts.update(query, {'$set': update}, multi=False)

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
            "id": body['id'],
            "event": body['event'],
            "severity": body['severity'],
            "value": body['value'],
            "text": body['text'],
            "createTime": body['createTime'],
            "receiveTime": body['receiveTime'],
        }]
        body['_id'] = body['id']
        del body['id']

        return self.db.alerts.insert(body)

    def duplicate_alert(self, environment, resource, event, update):

        # FIXME - no native find_and_modify method in this version of pymongo
        no_obj_error = "No matching object found"
        response = self.db.command("findAndModify", 'alerts',
                                   allowable_errors=[no_obj_error],
                                   query={"environment": environment, "resource": resource, "event": event},
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

    def update_status(self, alertid=None, environment=None, resource=None, event=None, status=None):

        update_time = datetime.datetime.utcnow()
        update_time = update_time.replace(tzinfo=pytz.utc)

        if alertid:
            query = {"_id": alertid}
        else:
            query = {"environment": environment, "resource": resource,
                     '$or': [{"event": event}, {"correlatedEvents": event}]}

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

        response = self.db.heartbeats.find({}, {"_id": 0})
        for heartbeat in response:
            heartbeats.append(heartbeat)
        return heartbeats

    def update_hb(self, origin, version, create_time, receive_time):

        query = {"origin": origin}
        update = {"origin": origin, "version": version, "createTime": create_time, "receiveTime": receive_time}

        try:
            self.db.heartbeats.update(query, update, True)
        except pymongo.errors.OperationFailure, e:
            LOG.error('MongoDB error: %s', e)

    # TODO(nsatterl): is this needed?
    # def save_heartbeat(self, heartbeat):
    #
    #     body = heartbeat.get_body()
    #     body['_id'] = body['id']
    #     del body['id']
    #
    #     return self.db.heartbeats.insert(body, safe=True)

    def disconnect(self):

        if self.conn.alive():
            self.conn.disconnect()

        LOG.info('Mongo disconnected.')
