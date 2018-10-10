
import os
import platform
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

from flask import current_app

from alerta.app import db
from alerta.database.base import Query
from alerta.utils.format import DateTime
from alerta.utils.response import absolute_url

MAX_LATENCY = 2000  # ms

JSON = Dict[str, Any]


class Heartbeat:

    def __init__(self, origin: str=None, tags: List[str]=None, create_time: datetime=None, timeout: int=None, customer: str=None, **kwargs) -> None:
        self.id = kwargs.get('id', str(uuid4()))
        self.origin = origin or '{}/{}'.format(os.path.basename(sys.argv[0]), platform.uname()[1])
        self.tags = tags or list()
        self.event_type = kwargs.get('event_type', kwargs.get('type', None)) or 'Heartbeat'
        self.create_time = create_time or datetime.utcnow()
        self.timeout = timeout or current_app.config['HEARTBEAT_TIMEOUT']
        self.receive_time = kwargs.get('receive_time', None) or datetime.utcnow()
        self.customer = customer

    @property
    def latency(self) -> int:
        return int((self.receive_time - self.create_time).total_seconds() * 1000)

    @property
    def since(self) -> timedelta:
        since = datetime.utcnow() - self.receive_time
        return since - timedelta(microseconds=since.microseconds)

    @property
    def status(self) -> str:
        if self.latency > MAX_LATENCY:
            return 'slow'
        elif self.since.total_seconds() > self.timeout:
            return 'expired'  # aka 'stale'
        else:
            return 'ok'

    @classmethod
    def parse(cls, json: JSON) -> 'Heartbeat':
        if not isinstance(json.get('tags', []), list):
            raise ValueError('tags must be a list')
        if not isinstance(json.get('timeout') if json.get('timeout', None) is not None else 0, int):
            raise ValueError('timeout must be an integer')
        if json.get('customer', None) == '':
            raise ValueError('customer must not be an empty string')

        return Heartbeat(
            origin=json.get('origin', None),
            tags=json.get('tags', list()),
            create_time=DateTime.parse(json['createTime']) if 'createTime' in json else None,
            timeout=json.get('timeout', None),
            customer=json.get('customer', None)
        )

    @property
    def serialize(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'href': absolute_url('/heartbeat/' + self.id),
            'origin': self.origin,
            'tags': self.tags,
            'type': self.event_type,
            'createTime': self.create_time,
            'timeout': self.timeout,
            'receiveTime': self.receive_time,
            'customer': self.customer,
            'latency': self.latency,
            'since': self.since,
            'status': self.status
        }

    def __repr__(self) -> str:
        return 'Heartbeat(id={!r}, origin={!r}, create_time={!r}, timeout={!r}, customer={!r})'.format(
            self.id, self.origin, self.create_time, self.timeout, self.customer)

    @classmethod
    def from_document(cls, doc: Dict[str, Any]) -> 'Heartbeat':
        return Heartbeat(
            id=doc.get('id', None) or doc.get('_id'),
            origin=doc.get('origin', None),
            tags=doc.get('tags', list()),
            event_type=doc.get('type', None),
            create_time=doc.get('createTime', None),
            timeout=doc.get('timeout', None),
            receive_time=doc.get('receiveTime', None),
            customer=doc.get('customer', None)
        )

    @classmethod
    def from_record(cls, rec) -> 'Heartbeat':
        return Heartbeat(
            id=rec.id,
            origin=rec.origin,
            tags=rec.tags,
            event_type=rec.type,
            create_time=rec.create_time,
            timeout=rec.timeout,
            receive_time=rec.receive_time,
            customer=rec.customer
        )

    @classmethod
    def from_db(cls, r: Union[Dict, Tuple]) -> 'Heartbeat':
        if isinstance(r, dict):
            return cls.from_document(r)
        elif isinstance(r, tuple):
            return cls.from_record(r)

    # create/update a heartbeat
    def create(self) -> 'Heartbeat':
        return Heartbeat.from_db(db.upsert_heartbeat(self))

    # retrieve an heartbeat
    @staticmethod
    def find_by_id(id: str, customers: List[str]=None) -> Optional['Heartbeat']:
        return Heartbeat.from_db(db.get_heartbeat(id, customers))

    # search heartbeats
    @staticmethod
    def find_all(query: Query=None) -> List['Heartbeat']:
        return [Heartbeat.from_db(heartbeat) for heartbeat in db.get_heartbeats(query)]

    # delete a heartbeat
    def delete(self) -> bool:
        return db.delete_heartbeat(self.id)
