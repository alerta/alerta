from datetime import datetime, time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

from alerta.app import db
from alerta.database.base import Query
from alerta.utils.response import absolute_url

JSON = Dict[str, Any]


class TwilioRuleStatus(str, Enum):

    Active = 'active'
    Deactive = 'deactive'


class TwilioRule:
    def __init__(self, environment: str, from_number: str, to_numbers: List[str], **kwargs) -> None:
        if not environment:
            raise ValueError('Missing mandatory value for "environment"')
        if not from_number:
            raise ValueError('Missing mandatory value for "from_number"')
        if not type(to_numbers) == list:
            raise ValueError('Missing mandatory value for "to_numbers"')

        self.id = kwargs.get('id') or str(uuid4())
        self.type = kwargs.get('type') or 'sms'
        self.environment = environment
        self.from_number = from_number
        self.to_numbers = to_numbers
        self.start_time: time = kwargs.get('start_time') or None
        self.end_time: time = kwargs.get('end_time') or None
        self.severity = kwargs.get('severity') or list()
        self.service = kwargs.get('service', None) or list()
        self.resource = kwargs.get('resource', None)
        self.event = kwargs.get('event', None)
        self.group = kwargs.get('group', None)
        self.tags = kwargs.get('tags', None) or list()
        self.customer = kwargs.get('customer', None)
        self.days = kwargs.get('days', None) or list()

        self.user = kwargs.get('user', None)
        self.create_time = kwargs['create_time'] if 'create_time' in kwargs else datetime.utcnow()
        self.text = kwargs.get('text', None)

        if self.environment:
            self.priority = 1
        if self.resource and not self.event:
            self.priority = 2
        elif self.service:
            self.priority = 3
        elif self.event and not self.resource:
            self.priority = 4
        elif self.group:
            self.priority = 5
        elif self.resource and self.event:
            self.priority = 6
        elif self.tags:
            self.priority = 7

    @property
    def status(self):
        return TwilioRuleStatus.Active

    @classmethod
    def parse(cls, json: JSON) -> 'TwilioRule':
        if not isinstance(json.get('service', []), list):
            raise ValueError('service must be a list')
        if not isinstance(json.get('tags', []), list):
            raise ValueError('tags must be a list')
        twilio_rule = TwilioRule(
            id=json.get('id', None),
            environment=json['environment'],
            type=json['type'],
            from_number=json['fromNumber'],
            to_numbers=json['toNumbers'],
            severity=json.get('severity', list()),
            service=json.get('service', list()),
            resource=json.get('resource', None),
            event=json.get('event', None),
            group=json.get('group', None),
            tags=json.get('tags', list()),
            customer=json.get('customer', None),
            start_time=(
                datetime.strptime(json['startTime'], '%H:%M').time() if json['startTime'] is not None and json['startTime'] != '' else None
            )
            if 'startTime' in json
            else None,
            end_time=(datetime.strptime(json['endTime'], '%H:%M').time() if json['endTime'] is not None and json['endTime'] != '' else None)
            if 'endTime' in json
            else None,
            duration=json.get('duration', None),
            user=json.get('user', None),
            text=json.get('text', None),
            days=json.get('days', None),
        )
        return twilio_rule

    @property
    def serialize(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'type': self.type,
            'href': absolute_url('/twiliorule/' + self.id),
            'priority': self.priority,
            'environment': self.environment,
            'fromNumber': self.from_number,
            'toNumbers': self.to_numbers,
            'service': self.service,
            'severity': self.severity,
            'resource': self.resource,
            'event': self.event,
            'group': self.group,
            'tags': self.tags,
            'customer': self.customer,
            'status': self.status,
            'user': self.user,
            'createTime': self.create_time,
            'text': self.text,
            'startTime': self.start_time.strftime('%H:%M') if self.start_time is not None else None,
            'endTime': self.end_time.strftime('%H:%M') if self.end_time is not None else None,
            'days': self.days,
        }

    def __repr__(self) -> str:
        more = ''
        if self.service:
            more += 'service=%r, ' % self.service
        if self.resource:
            more += 'resource=%r, ' % self.resource
        if self.event:
            more += 'event=%r, ' % self.event
        if self.group:
            more += 'group=%r, ' % self.group
        if self.tags:
            more += 'tags=%r, ' % self.tags
        if self.customer:
            more += 'customer=%r, ' % self.customer
        if self.severity:
            more += 'severity=%r, ' % self.severity

        return 'TwilioRule(id={!r}, priority={!r}, status={!r}, environment={!r}, from_number={!r}, to_numbers={!r}, {})'.format(
            self.id,
            self.priority,
            self.status,
            self.environment,
            self.from_number,
            self.to_numbers,
            more,
        )

    @classmethod
    def from_document(cls, doc: Dict[str, Any]) -> 'TwilioRule':
        return TwilioRule(
            id=doc.get('id', None) or doc.get('_id'),
            priority=doc.get('priority', None),
            environment=doc['environment'],
            type=doc['type'],
            from_number=doc['fromNumber'],
            to_numbers=doc['toNumbers'],
            service=doc.get('service', list()),
            severity=doc.get('severity', list()),
            resource=doc.get('resource', None),
            event=doc.get('event', None),
            group=doc.get('group', None),
            tags=doc.get('tags', list()),
            customer=doc.get('customer', None),
            user=doc.get('user', None),
            create_time=doc.get('createTime', None),
            text=doc.get('text', None),
            start_time=(
                datetime.strptime(f'{doc["startTime"] :.2f}'.replace('.', ':'), '%H:%M').time() if doc['startTime'] is not None else None
            )
            if 'startTime' in doc
            else None,
            end_time=(datetime.strptime(f'{doc["endTime"] :.2f}'.replace('.', ':'), '%H:%M').time() if doc['endTime'] is not None else None)
            if 'endTime' in doc
            else None,
            days=doc.get('days', None),
        )

    @classmethod
    def from_record(cls, rec) -> 'TwilioRule':
        return TwilioRule(
            id=rec.id,
            priority=rec.priority,
            environment=rec.environment,
            type=rec.type,
            from_number=rec.from_number,
            to_numbers=rec.to_numbers,
            service=rec.service,
            severity=rec.severity,
            resource=rec.resource,
            event=rec.event,
            group=rec.group,
            tags=rec.tags,
            customer=rec.customer,
            user=rec.user,
            create_time=rec.create_time,
            text=rec.text,
            start_time=rec.start_time,
            end_time=rec.end_time,
            days=rec.days,
        )

    @classmethod
    def from_db(cls, r: Union[Dict, Tuple]) -> 'TwilioRule':
        if isinstance(r, dict):
            return cls.from_document(r)
        elif isinstance(r, tuple):
            return cls.from_record(r)

    # create a twilio rule
    def create(self) -> 'TwilioRule':
        return TwilioRule.from_db(db.create_twilio_rule(self))

    # get a twilio rule
    @staticmethod
    def find_by_id(id: str, customers: List[str] = None) -> Optional['TwilioRule']:
        return TwilioRule.from_db(db.get_twilio_rule(id, customers))

    @staticmethod
    def find_all(query: Query = None, page: int = 1, page_size: int = 1000) -> List['TwilioRule']:
        return [TwilioRule.from_db(twilio_rule) for twilio_rule in db.get_twilio_rules(query, page, page_size)]

    @staticmethod
    def count(query: Query = None) -> int:
        return db.get_twilio_rules_count(query)

    def update(self, **kwargs) -> 'TwilioRule':
        return TwilioRule.from_db(db.update_twilio_rule(self.id, **kwargs))

    def delete(self) -> bool:
        return db.delete_twilio_rule(self.id)
