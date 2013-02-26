import sys
import datetime
import json
import pytz

import pymongo

from alerta.common import log as logging
from alerta.common import config
from alerta.alert import Alert
from alerta.common.utils import DateEncoder

LOG = logging.getLogger(__name__)
CONF = config.CONF


class Database(object):

    def __init__(self):

        # Connect to MongoDB
        try:
            self.conn = pymongo.MongoClient(CONF.mongo_host, CONF.mongo_port)
            self.db = self.conn.monitoring  # TODO(nsatterl): make 'monitoring' a SYSTEM DEFAULT
        except Exception, e:
            LOG.error('MongoDB Client error : %s', e)
            sys.exit(1)

        if self.conn.alive():
            LOG.info('Connected to MongoDB server %s:%s', CONF.mongo_host, CONF.mongo_port)
            LOG.debug('MongoDB %s, databases available: %s', self.conn.server_info()['version'], ', '.join(self.conn.database_names()))

        self.db.alerts.create_index([('environment', pymongo.DESCENDING), ('resource', pymongo.DESCENDING),
                                     ('event', pymongo.DESCENDING)])   # TODO(nsatterl): verify perf of this index

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

    def get_alert(self, environment, resource, event, severity=None):

        if severity:
            response = self.db.alerts.find_one({"environment": environment, "resource": resource, "event": event, "severity": severity})
        else:
            response = self.db.alerts.find_one({"environment": environment, "resource": resource, "event": event})

        if not response:
            LOG.warning('Alert not found with environment, resource, event, severity = %s %s %s %s', environment, resource, event, severity)
            return

        return Alert(
            alertid=response['_id'],
            resource=response['resource'],
            event=response['event'],
            correlate=response['correlatedEvents'],
            group=response['group'],
            value=response['value'],
            severity=response['severity'],        # convert to severity type
            environment=response['environment'],
            service=response['service'],
            text=response['text'],
            event_type=response['type'],
            tags=response['tags'],
            origin=response['origin'],
            threshold_info=response['thresholdInfo'],
            summary=response['summary'],
            timeout=response['timeout'],
            create_time=response['createTime'],
            receive_time=response['receiveTime'],
            last_receive_time=response['lastReceiveTime'],
            trend_indication=response['trendIndication'],
        )

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

        return self.db.alerts.insert(body, safe=True)

    def modify_alert(self, environment, resource, event, **kwargs):

        # FIXME - no native find_and_modify method in this version of pymongo
        no_obj_error = "No matching object found"
        return self.db.command("findAndModify", 'alerts',
                               allowable_errors=[no_obj_error],
                               query={"environment": environment, "resource": resource,
                                      '$or': [{"event": event}, {"correlatedEvents": event}]},
                               update={'$set': kwargs,
                                       '$push': {"history": {
                                                    "createTime": kwargs['createTime'],
                                                    "receiveTime": kwargs['receiveTime'],
                                                    "severity": kwargs['severity'],
                                                    "event": kwargs['event'],
                                                    "value": kwargs['value'],
                                                    "text": kwargs['text'],
                                                    "id": kwargs['lastReceiveId']
                                                }
                                       }
                               },
                               new=True,
                               fields={"history": 0})['value']

    def duplicate_alert(self, environment, resource, event, **kwargs):

        # FIXME - no native find_and_modify method in this version of pymongo
        no_obj_error = "No matching object found"
        return self.db.command("findAndModify", 'alerts',
                               allowable_errors=[no_obj_error],
                               query={"environment": environment, "resource": resource, "event": event},
                               update={'$set': kwargs,
                                       '$inc': {"duplicateCount": 1}},
                               new=True,
                               fields={"history": 0})['value']

    def update_status(self, environment, resource, event, status):

        update_time = datetime.datetime.utcnow()
        update_time = update_time.replace(tzinfo=pytz.utc)

        LOG.info('Alert status for %s %s %s alert set to %s', environment, resource, event, status)

        query = {"environment": environment, "resource": resource,
                 '$or': [{"event": event}, {"correlatedEvents": event}]}
        update = {'$set': {"status": status}, '$push': {"history": {"status": status, "updateTime": update_time}}}

        LOG.debug('query = %s, update = %s', query, update)

        try:
            self.db.alerts.update(query, update)
        except pymongo.errors.OperationFailure, e:
            LOG.error('MongoDB error: %s', e)

    def update_hb(self):

        pass

    def disconnect(self):

        if self.conn.alive():
            self.conn.disconnect()

        LOG.info('Database disconnected.')
