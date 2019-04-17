
import os
import platform
import sys
from datetime import datetime
from typing import Optional  # noqa
from typing import Any, Dict, List, Tuple, Union
from uuid import uuid4

from flask import current_app, g

from alerta.app import alarm_model, db
from alerta.database.base import Query
from alerta.models.history import History, RichHistory
from alerta.utils.format import DateTime
from alerta.utils.hooks import status_change_hook
from alerta.utils.response import absolute_url

JSON = Dict[str, Any]
NoneType = type(None)


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
        for attr in ['create_time', 'receive_time', 'last_receive_time']:
            if not isinstance(kwargs.get(attr), (datetime, NoneType)):  # type: ignore
                raise ValueError("Attribute '{}' must be datetime type".format(attr))

        timeout = kwargs.get('timeout') if kwargs.get('timeout') is not None else current_app.config['ALERT_TIMEOUT']
        try:
            timeout = int(timeout)  # type: ignore
        except ValueError:
            raise ValueError("Could not convert 'timeout' value of '{}' to an integer".format(timeout))
        if timeout < 0:
            raise ValueError("Invalid negative 'timeout' value ({})".format(timeout))

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
        self.timeout = timeout
        self.raw_data = kwargs.get('raw_data', None)
        self.customer = kwargs.get('customer', None)

        self.duplicate_count = kwargs.get('duplicate_count', None)
        self.repeat = kwargs.get('repeat', None)
        self.previous_severity = kwargs.get('previous_severity', None)
        self.trend_indication = kwargs.get('trend_indication', None)
        self.receive_time = kwargs.get('receive_time', None) or datetime.utcnow()
        self.last_receive_id = kwargs.get('last_receive_id', None)
        self.last_receive_time = kwargs.get('last_receive_time', None)
        self.update_time = kwargs.get('update_time', None)
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
            'updateTime': self.update_time,
            'history': [h.serialize for h in sorted(self.history, key=lambda x: x.update_time)]
        }

    def get_id(self, short: bool=False) -> str:
        return self.id[:8] if short else self.id

    def get_body(self, history: bool=True) -> Dict[str, Any]:
        body = self.serialize
        body.update({
            key: DateTime.iso8601(body[key]) for key in ['createTime', 'lastReceiveTime', 'receiveTime', 'updateTime'] if body[key]
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
            update_time=doc.get('updateTime', None),
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
            update_time=getattr(rec, 'update_time'),
            history=[History.from_db(h) for h in rec.history]
        )

    @classmethod
    def from_db(cls, r: Union[Dict, Tuple]) -> 'Alert':
        if isinstance(r, dict):
            return cls.from_document(r)
        elif isinstance(r, tuple):
            return cls.from_record(r)

    def is_duplicate(self) -> Optional['Alert']:
        """Return duplicate alert or None"""
        return Alert.from_db(db.is_duplicate(self))

    def is_correlated(self) -> Optional['Alert']:
        """Return correlated alert or None"""
        return Alert.from_db(db.is_correlated(self))

    def is_flapping(self, window: int=1800, count: int=2) -> bool:
        return db.is_flapping(self, window, count)

    def get_status_and_value(self):
        return [(h.status, h.value) for h in self.get_alert_history(self, page=1, page_size=10) if h.status]

    def _get_hist_info(self, action=None):
        h_loop = self.get_alert_history(alert=self)
        if len(h_loop) == 1:
            return h_loop[0].status, h_loop[0].value, None
        if action == 'unack':
            find = 'ack'
        elif action == 'unshelve':
            find = 'shelve'
        else:
            find = None
        for h, h_next in zip(h_loop, h_loop[1:]):
            if not find or h.change_type == find:
                return h_loop[0].status, h_loop[0].value, h_next.status
        return None, None, None

    # de-duplicate an alert
    def deduplicate(self, duplicate_of) -> 'Alert':
        now = datetime.utcnow()

        status, previous_value, previous_status = self._get_hist_info()

        _, new_status = alarm_model.transition(
            alert=self,
            current_status=status,
            previous_status=previous_status
        )

        self.repeat = True
        self.last_receive_id = self.id
        self.last_receive_time = now

        if new_status != status:
            text = 'duplicate alert (with status change)'
            r = status_change_hook.send(duplicate_of, status=new_status, text=text)
            _, (_, new_status, text) = r[0]
            self.update_time = now

            history = History(
                id=self.id,
                event=self.event,
                severity=self.severity,
                status=new_status,
                value=self.value,
                text=text,
                change_type='status',
                update_time=self.create_time,
                user=g.login,
            )  # type: Optional[History]

        elif current_app.config['HISTORY_ON_VALUE_CHANGE'] and self.value != previous_value:
            history = History(
                id=self.id,
                event=self.event,
                severity=self.severity,
                status=status,
                value=self.value,
                text='duplicate alert (with value change)',
                change_type='value',
                update_time=self.create_time,
                user=g.login
            )
        else:
            history = None

        self.status = new_status
        return Alert.from_db(db.dedup_alert(self, history))

    # correlate an alert
    def update(self, correlate_with) -> 'Alert':
        now = datetime.utcnow()

        self.previous_severity = db.get_severity(self)
        self.trend_indication = alarm_model.trend(self.previous_severity, self.severity)

        status, _, previous_status = self._get_hist_info()

        _, new_status = alarm_model.transition(
            alert=self,
            current_status=status,
            previous_status=previous_status
        )

        self.duplicate_count = 0
        self.repeat = False
        self.receive_time = now
        self.last_receive_id = self.id
        self.last_receive_time = now
        text = 'correlated alert'

        if new_status != status:
            r = status_change_hook.send(correlate_with, status=new_status, text=text)
            _, (_, new_status, text) = r[0]
            self.update_time = now

        history = [History(
            id=self.id,
            event=self.event,
            severity=self.severity,
            status=new_status,
            value=self.value,
            text=text,
            change_type='severity',
            update_time=self.create_time,
            user=g.login
        )]

        self.status = new_status
        return Alert.from_db(db.correlate_alert(self, history))

    # create an alert
    def create(self) -> 'Alert':
        now = datetime.utcnow()

        trend_indication = alarm_model.trend(alarm_model.DEFAULT_PREVIOUS_SEVERITY, self.severity)

        _, self.status = alarm_model.transition(
            alert=self
        )

        self.duplicate_count = 0
        self.repeat = False
        self.previous_severity = alarm_model.DEFAULT_PREVIOUS_SEVERITY
        self.trend_indication = trend_indication
        self.receive_time = now
        self.last_receive_id = self.id
        self.last_receive_time = now
        self.update_time = now

        self.history = [History(
            id=self.id,
            event=self.event,
            severity=self.severity,
            status=self.status,
            value=self.value,
            text='new alert',
            change_type='new',
            update_time=self.create_time,
            user=g.login
        )]

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
        now = datetime.utcnow()

        timeout = timeout or current_app.config['ALERT_TIMEOUT']
        history = History(
            id=self.id,
            event=self.event,
            severity=self.severity,
            status=status,
            value=self.value,
            text=text,
            change_type='status',
            update_time=now,
            user=g.login
        )
        return db.set_status(self.id, status, timeout, update_time=now, history=history)

    # tag an alert
    def tag(self, tags: List[str]) -> bool:
        return db.tag_alert(self.id, tags)

    # untag an alert
    def untag(self, tags: List[str]) -> bool:
        return db.untag_alert(self.id, tags)

    # update alert attributes
    def update_attributes(self, attributes: Dict[str, Any]) -> bool:
        return db.update_attributes(self.id, self.attributes, attributes)

    # add note
    def add_note(self, note: str) -> bool:
        history = History(
            id=self.id,
            event=self.event,
            severity=self.severity,
            status=self.status,
            value=self.value,
            text=note,
            change_type='note',
            update_time=datetime.utcnow(),
            user=g.login
        )
        return db.add_history(self.id, history)

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

    @staticmethod
    def get_alert_history(alert, page=1, page_size=100):
        return [RichHistory.from_db(hist) for hist in db.get_alert_history(alert, page, page_size)]

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

    # get groups
    @staticmethod
    def get_groups(query: Query=None) -> List[str]:
        return db.get_alert_groups(query)

    # get tags
    @staticmethod
    def get_tags(query: Query=None) -> List[str]:
        return db.get_alert_tags(query)

    @staticmethod
    def housekeeping(expired_threshold: int=2, info_threshold: int=12) -> None:
        now = datetime.utcnow()
        expired, unshelved = db.housekeeping(expired_threshold, info_threshold)

        for (id, event, last_receive_id) in expired:
            history = History(
                id=last_receive_id,
                event=event,
                status='expired',
                text='auto-expired after timeout',
                change_type='status',
                update_time=now,
                user=g.login
            )
            db.set_status(id, 'expired', timeout=current_app.config['ALERT_TIMEOUT'], update_time=now, history=history)

        for (id, event, last_receive_id) in unshelved:
            # as per ISA 18.2 recommendation 11.7.3 auto-unshelved alarms transition to open, not previous status
            history = History(
                id=last_receive_id,
                event=event,
                status='open',
                text='auto-unshelved after timeout',
                change_type='status',
                update_time=now,
                user=g.login
            )
            db.set_status(id, 'open', timeout=current_app.config['ALERT_TIMEOUT'], update_time=now, history=history)

    def from_status(self, status: str, text: str='', timeout: int=None) -> 'Alert':
        now = datetime.utcnow()

        self.timeout = timeout or current_app.config['ALERT_TIMEOUT']
        history = [History(
            id=self.id,
            event=self.event,
            severity=self.severity,
            status=status,
            value=self.value,
            text=text,
            change_type='status',
            update_time=now,
            user=g.login
        )]
        return Alert.from_db(db.set_alert(
            id=self.id,
            severity=self.severity,
            status=status,
            tags=self.tags,
            attributes=self.attributes,
            timeout=timeout,
            previous_severity=self.previous_severity,
            update_time=now,
            history=history)
        )

    def from_action(self, action: str, text: str='', timeout: int=None) -> 'Alert':
        now = datetime.utcnow()

        self.timeout = timeout or current_app.config['ALERT_TIMEOUT']

        status, _, previous_status = self._get_hist_info(action)

        new_severity, new_status = alarm_model.transition(
            alert=self,
            current_status=status,
            previous_status=previous_status,
            action=action
        )

        r = status_change_hook.send(self, status=new_status, text=text)
        _, (_, new_status, text) = r[0]

        history = [History(
            id=self.id,
            event=self.event,
            severity=new_severity,
            status=new_status,
            value=self.value,
            text=text,
            change_type=action,
            update_time=now,
            user=g.login
        )]

        return Alert.from_db(db.set_alert(
            id=self.id,
            severity=new_severity,
            status=new_status,
            tags=self.tags,
            attributes=self.attributes,
            timeout=timeout,
            previous_severity=self.severity if new_severity != self.severity else self.previous_severity,
            update_time=now,
            history=history)
        )
