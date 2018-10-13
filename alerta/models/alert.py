
import os
import platform
import sys
from datetime import datetime
from typing import Any, Dict, List, Tuple, Union
from uuid import uuid4

from flask import current_app

from alerta.app import alarm_model, db
from alerta.database.base import Query
from alerta.models.history import History, RichHistory
from alerta.utils.format import DateTime
from alerta.utils.response import absolute_url

JSON = Dict[str, Any]


class Alert:

    def __init__(self, resource: str, event: str, **kwargs) -> None:

        if not resource:
            raise ValueError('Missing mandatory value for "resource"')
        if not event:
            raise ValueError('Missing mandatory value for "event"')
        if any(['.' in key for key in kwargs.get('attributes', dict()).keys()]) \
                or any(['$' in key for key in kwargs.get('attributes', dict()).keys()]):
            raise ValueError('Attribute keys must not contain "." or "$"')
        if isinstance(kwargs.get('value', None), int):
            kwargs['value'] = str(kwargs['value'])

        self.id = kwargs.get('id', None) or str(uuid4())
        self.resource = resource
        self.event = event
        self.environment = kwargs.get('environment', None) or ''
        self.severity = kwargs.get('severity', None) or alarm_model.DEFAULT_NORMAL_SEVERITY
        self.correlate = kwargs.get('correlate', None) or list()
        if self.correlate and event not in self.correlate:
            self.correlate.append(event)
        self.status = kwargs.get('status', None) or alarm_model.DEFAULT_STATUS
        self.service = kwargs.get('service', None) or list()
        self.group = kwargs.get('group', None) or 'Misc'
        self.value = kwargs.get('value', None)
        self.text = kwargs.get('text', None) or ''
        self.tags = kwargs.get('tags', None) or list()
        self.attributes = kwargs.get('attributes', None) or dict()
        self.origin = kwargs.get('origin', None) or '{}/{}'.format(os.path.basename(sys.argv[0]), platform.uname()[1])
        self.event_type = kwargs.get('event_type', kwargs.get('type', None)) or 'exceptionAlert'
        self.create_time = kwargs.get('create_time', None) or datetime.utcnow()
        self.timeout = kwargs.get('timeout', None) or current_app.config['ALERT_TIMEOUT']
        self.raw_data = kwargs.get('raw_data', None)
        self.customer = kwargs.get('customer', None)

        self.duplicate_count = kwargs.get('duplicate_count', None)
        self.repeat = kwargs.get('repeat', None)
        self.previous_severity = kwargs.get('previous_severity', None)
        self.trend_indication = kwargs.get('trend_indication', None)
        self.receive_time = kwargs.get('receive_time', None) or datetime.utcnow()
        self.last_receive_id = kwargs.get('last_receive_id', None)
        self.last_receive_time = kwargs.get('last_receive_time', None)
        self.history = kwargs.get('history', None) or list()

    @classmethod
    def parse(cls, json: JSON) -> 'Alert':
        if not isinstance(json.get('correlate', []), list):
            raise ValueError('correlate must be a list')
        if not isinstance(json.get('service', []), list):
            raise ValueError('service must be a list')
        if not isinstance(json.get('tags', []), list):
            raise ValueError('tags must be a list')
        if not isinstance(json.get('attributes', {}), dict):
            raise ValueError('attributes must be a JSON object')
        if not isinstance(json.get('timeout') if json.get('timeout', None) is not None else 0, int):
            raise ValueError('timeout must be an integer')
        if json.get('customer', None) == '':
            raise ValueError('customer must not be an empty string')

        return Alert(
            id=json.get('id', None),
            resource=json.get('resource', None),
            event=json.get('event', None),
            environment=json.get('environment', None),
            severity=json.get('severity', None),
            correlate=json.get('correlate', list()),
            status=json.get('status', None),
            service=json.get('service', list()),
            group=json.get('group', None),
            value=json.get('value', None),
            text=json.get('text', None),
            tags=json.get('tags', list()),
            attributes=json.get('attributes', dict()),
            origin=json.get('origin', None),
            event_type=json.get('type', None),
            create_time=DateTime.parse(json['createTime']) if 'createTime' in json else None,
            timeout=json.get('timeout', None),
            raw_data=json.get('rawData', None),
            customer=json.get('customer', None)
        )

    @property
    def serialize(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'href': absolute_url('/alert/' + self.id),
            'resource': self.resource,
            'event': self.event,
            'environment': self.environment,
            'severity': self.severity,
            'correlate': self.correlate,
            'status': self.status,
            'service': self.service,
            'group': self.group,
            'value': self.value,
            'text': self.text,
            'tags': self.tags,
            'attributes': self.attributes,
            'origin': self.origin,
            'type': self.event_type,
            'createTime': self.create_time,
            'timeout': self.timeout,
            'rawData': self.raw_data,
            'customer': self.customer,
            'duplicateCount': self.duplicate_count,
            'repeat': self.repeat,
            'previousSeverity': self.previous_severity,
            'trendIndication': self.trend_indication,
            'receiveTime': self.receive_time,
            'lastReceiveId': self.last_receive_id,
            'lastReceiveTime': self.last_receive_time,
            'history': [h.serialize for h in sorted(self.history, key=lambda x: x.update_time)]
        }

    def get_id(self, short: bool=False) -> str:
        return self.id[:8] if short else self.id

    def get_body(self, history: bool=True) -> Dict[str, Any]:
        body = self.serialize
        body.update({
            key: DateTime.iso8601(body[key]) for key in ['createTime', 'lastReceiveTime', 'receiveTime']
        })
        if not history:
            body['history'] = []
        return body

    def __repr__(self) -> str:
        return 'Alert(id={!r}, environment={!r}, resource={!r}, event={!r}, severity={!r}, status={!r}, customer={!r})'.format(
            self.id, self.environment, self.resource, self.event, self.severity, self.status, self.customer)

    @classmethod
    def from_document(cls, doc: Dict[str, Any]) -> 'Alert':
        return Alert(
            id=doc.get('id', None) or doc.get('_id'),
            resource=doc.get('resource', None),
            event=doc.get('event', None),
            environment=doc.get('environment', None),
            severity=doc.get('severity', None),
            correlate=doc.get('correlate', list()),
            status=doc.get('status', None),
            service=doc.get('service', list()),
            group=doc.get('group', None),
            value=doc.get('value', None),
            text=doc.get('text', None),
            tags=doc.get('tags', list()),
            attributes=doc.get('attributes', dict()),
            origin=doc.get('origin', None),
            event_type=doc.get('type', None),
            create_time=doc.get('createTime', None),
            timeout=doc.get('timeout', None),
            raw_data=doc.get('rawData', None),
            customer=doc.get('customer', None),
            duplicate_count=doc.get('duplicateCount', None),
            repeat=doc.get('repeat', None),
            previous_severity=doc.get('previousSeverity', None),
            trend_indication=doc.get('trendIndication', None),
            receive_time=doc.get('receiveTime', None),
            last_receive_id=doc.get('lastReceiveId', None),
            last_receive_time=doc.get('lastReceiveTime', None),
            history=[History.from_db(h) for h in doc.get('history', list())]
        )

    @classmethod
    def from_record(cls, rec) -> 'Alert':
        return Alert(
            id=rec.id,
            resource=rec.resource,
            event=rec.event,
            environment=rec.environment,
            severity=rec.severity,
            correlate=rec.correlate,
            status=rec.status,
            service=rec.service,
            group=rec.group,
            value=rec.value,
            text=rec.text,
            tags=rec.tags,
            attributes=dict(rec.attributes),
            origin=rec.origin,
            event_type=rec.type,
            create_time=rec.create_time,
            timeout=rec.timeout,
            raw_data=rec.raw_data,
            customer=rec.customer,
            duplicate_count=rec.duplicate_count,
            repeat=rec.repeat,
            previous_severity=rec.previous_severity,
            trend_indication=rec.trend_indication,
            receive_time=rec.receive_time,
            last_receive_id=rec.last_receive_id,
            last_receive_time=rec.last_receive_time,
            history=[History.from_db(h) for h in rec.history]
        )

    @classmethod
    def from_db(cls, r: Union[Dict, Tuple]) -> 'Alert':
        if isinstance(r, dict):
            return cls.from_document(r)
        elif isinstance(r, tuple):
            return cls.from_record(r)

    def is_duplicate(self) -> bool:
        return db.is_duplicate(self)

    def is_correlated(self) -> bool:
        return db.is_correlated(self)

    def is_flapping(self, window: int=1800, count: int=2) -> bool:
        return db.is_flapping(self, window, count)

    # de-duplicate an alert
    def deduplicate(self) -> 'Alert':
        now = datetime.utcnow()

        previous_status, previous_value = db.get_status_and_value(self)
        _, self.status = alarm_model.transition(
            previous_severity=self.severity,
            current_severity=self.severity,
            previous_status=previous_status,
            current_status=self.status
        )

        self.repeat = True
        self.last_receive_id = self.id
        self.last_receive_time = now

        from typing import Optional  # noqa

        if self.status != previous_status:
            history = History(
                id=self.id,
                event=self.event,
                status=self.status,
                text='duplicate alert with status change',
                change_type='status',
                update_time=self.create_time
            )  # type: Optional[History]
        elif current_app.config['HISTORY_ON_VALUE_CHANGE'] and self.value != previous_value:
            history = History(
                id=self.id,
                event=self.event,
                value=self.value,
                text='duplicate alert with value change',
                change_type='value',
                update_time=self.create_time
            )
        else:
            history = None
        return Alert.from_db(db.dedup_alert(self, history))

    # correlate an alert
    def update(self) -> 'Alert':
        now = datetime.utcnow()

        self.previous_severity = db.get_severity(self)
        previous_status = db.get_status(self)
        self.trend_indication = alarm_model.trend(self.previous_severity, self.severity)

        _, self.status = alarm_model.transition(
            previous_severity=self.previous_severity,
            current_severity=self.severity,
            previous_status=previous_status,
            current_status=self.status
        )

        self.duplicate_count = 0
        self.repeat = False
        self.receive_time = now
        self.last_receive_id = self.id
        self.last_receive_time = now

        history = [History(
            id=self.id,
            event=self.event,
            severity=self.severity,
            value=self.value,
            text=self.text,
            change_type='severity',
            update_time=self.create_time
        )]

        if self.status != previous_status:
            history.append(History(
                id=self.id,
                event=self.event,
                status=self.status,
                text='correlated alert status change',
                change_type='status',
                update_time=self.create_time
            ))

        return Alert.from_db(db.correlate_alert(self, history))

    # create an alert
    def create(self) -> 'Alert':
        if self.status == alarm_model.DEFAULT_STATUS:
            _, self.status = alarm_model.transition(
                previous_severity=alarm_model.DEFAULT_PREVIOUS_SEVERITY,
                current_severity=self.severity
            )
        trend_indication = alarm_model.trend(alarm_model.DEFAULT_PREVIOUS_SEVERITY, self.severity)

        self.duplicate_count = 0
        self.repeat = False
        self.previous_severity = alarm_model.DEFAULT_PREVIOUS_SEVERITY
        self.trend_indication = trend_indication
        self.receive_time = datetime.utcnow()
        self.last_receive_id = self.id
        self.last_receive_time = self.receive_time

        self.history = [History(
            id=self.id,
            event=self.event,
            severity=self.severity,
            value=self.value,
            text=self.text,
            change_type='severity',
            update_time=self.create_time
        )]

        self.history.append(History(
            id=self.id,
            event=self.event,
            status=self.status,
            text='new alert status change',
            change_type='status',
            update_time=self.create_time
        ))

        return Alert.from_db(db.create_alert(self))

    # retrieve an alert
    @staticmethod
    def find_by_id(id: str, customers: List[str]=None) -> 'Alert':
        return Alert.from_db(db.get_alert(id, customers))

    def is_blackout(self) -> bool:
        """Does this alert match a blackout period?"""
        if not current_app.config['NOTIFICATION_BLACKOUT']:
            if self.severity in current_app.config['BLACKOUT_ACCEPT']:
                return False
        return db.is_blackout_period(self)

    @property
    def is_suppressed(self) -> bool:
        """Is the alert status 'blackout'?"""
        return alarm_model.is_suppressed(self)

    # set alert status
    def set_status(self, status: str, text: str='', timeout: int=None) -> 'Alert':
        timeout = timeout or current_app.config['ALERT_TIMEOUT']
        history = History(
            id=self.id,
            event=self.event,
            status=status,
            text=text,
            change_type='status',
            update_time=datetime.utcnow()
        )
        return db.set_status(self.id, status, timeout, history)

    def set_severity_and_status(self, severity: str, status: str, text: str='', timeout: int=None) -> 'Alert':
        timeout = timeout or current_app.config['ALERT_TIMEOUT']
        history = History(
            id=self.id,
            event=self.event,
            severity=severity,
            status=status,
            text=text,
            change_type='action',
            update_time=datetime.utcnow()
        )
        return db.set_severity_and_status(self.id, severity, status, timeout, history)

    # tag an alert
    def tag(self, tags: List[str]) -> bool:
        return db.tag_alert(self.id, tags)

    # untag an alert
    def untag(self, tags: List[str]) -> bool:
        return db.untag_alert(self.id, tags)

    # update alert attributes
    def update_attributes(self, attributes: Dict[str, Any]) -> bool:
        return db.update_attributes(self.id, self.attributes, attributes)

    # delete an alert
    def delete(self) -> bool:
        return db.delete_alert(self.id)

    # bulk tag
    @staticmethod
    def tag_find_all(query, tags):
        return db.tag_alerts(query, tags)

    # bulk untag
    @staticmethod
    def untag_find_all(query, tags):
        return db.untag_alerts(query, tags)

    # bulk update attributes
    @staticmethod
    def update_attributes_find_all(query, attributes):
        return db.update_attributes_by_query(query, attributes)

    # bulk delete
    @staticmethod
    def delete_find_all(query=None):
        return db.delete_alerts(query)

    # search alerts
    @staticmethod
    def find_all(query: Query=None, page: int=1, page_size: int=1000) -> List['Alert']:
        return [Alert.from_db(alert) for alert in db.get_alerts(query, page, page_size)]

    # list alert history
    @staticmethod
    def get_history(query: Query=None, page=1, page_size=1000) -> List[RichHistory]:
        return [RichHistory.from_db(hist) for hist in db.get_history(query, page, page_size)]

    # get total count
    @staticmethod
    def get_count(query: Query=None) -> Dict[str, Any]:
        return db.get_count(query)

    # get severity counts
    @staticmethod
    def get_counts_by_severity(query: Query=None) -> Dict[str, Any]:
        return db.get_counts_by_severity(query)

    # get status counts
    @staticmethod
    def get_counts_by_status(query: Query=None) -> Dict[str, Any]:
        return db.get_counts_by_status(query)

    # top 10 alerts
    @staticmethod
    def get_top10_count(query: Query=None) -> List[Dict[str, Any]]:
        return db.get_topn_count(query, topn=10)

    # top 10 flapping
    @staticmethod
    def get_top10_flapping(query: Query=None) -> List[Dict[str, Any]]:
        return db.get_topn_flapping(query, topn=10)

    # top 10 standing
    @staticmethod
    def get_top10_standing(query: Query=None) -> List[Dict[str, Any]]:
        return db.get_topn_standing(query, topn=10)

    # get environments
    @staticmethod
    def get_environments(query: Query=None) -> List[str]:
        return db.get_environments(query)

    # get services
    @staticmethod
    def get_services(query: Query=None) -> List[str]:
        return db.get_services(query)

    # get tags
    @staticmethod
    def get_tags(query: Query=None) -> List[str]:
        return db.get_tags(query)

    @staticmethod
    def housekeeping(expired_threshold: int=2, info_threshold: int=12) -> None:
        expired, unshelved = db.housekeeping(expired_threshold, info_threshold)

        for (id, event, last_receive_id) in expired:
            history = History(
                id=last_receive_id,
                event=event,
                status='expired',
                text='expired after timeout',
                change_type='status',
                update_time=datetime.utcnow()
            )
            db.set_status(id, 'expired', timeout=current_app.config['ALERT_TIMEOUT'], history=history)

        for (id, event, last_receive_id) in unshelved:
            history = History(
                id=last_receive_id,
                event=event,
                status='open',
                text='unshelved after timeout',
                change_type='status',
                update_time=datetime.utcnow()
            )
            db.set_status(id, 'open', timeout=current_app.config['ALERT_TIMEOUT'], history=history)

    def from_status(self, status: str, text: str='', timeout: int=None) -> 'Alert':
        self.timeout = timeout or current_app.config['ALERT_TIMEOUT']
        history = History(
            id=self.id,
            event=self.event,
            status=status,
            text=text,
            change_type='status',
            update_time=datetime.utcnow()
        )
        return Alert.from_db(db.set_alert(self.id, self.severity, status, self.tags, self.attributes, timeout, history))

    def from_action(self, action: str, text: str='', timeout: int=None) -> 'Alert':
        self.timeout = timeout or current_app.config['ALERT_TIMEOUT']
        previous_status = db.get_status(self)

        severity, status = alarm_model.transition(
            previous_severity=self.previous_severity,
            current_severity=self.severity,
            previous_status=previous_status,
            current_status=self.status,
            action=action
        )

        history = History(
            id=self.id,
            event=self.event,
            severity=self.severity if self.previous_severity != self.severity else None,
            status=self.status,
            text=text,
            change_type='action',
            update_time=datetime.utcnow()
        )
        return Alert.from_db(db.set_alert(self.id, severity, status, self.tags, self.attributes, timeout, history))
