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

JSON = Dict[str, Any]


class Heartbeat:

    def __init__(self, origin: str = None, tags: List[str] = None, create_time: datetime = None, timeout: int = None, customer: str = None, **kwargs) -> None:

        if any(['.' in key for key in kwargs.get('attributes', dict()).keys()]) \
                or any(['$' in key for key in kwargs.get('attributes', dict()).keys()]):
            raise ValueError('Attribute keys must not contain "." or "$"')

        timeout = timeout if timeout is not None else current_app.config['HEARTBEAT_TIMEOUT']
        max_latency = current_app.config['HEARTBEAT_MAX_LATENCY']

        try:
            timeout = int(timeout)
        except ValueError:
            raise ValueError("Could not convert 'timeout' value of '{}' to an integer".format(timeout))
        if timeout < 0:
            raise ValueError("Invalid negative 'timeout' value ({})".format(timeout))

        try:
            max_latency = int(max_latency)
        except ValueError:
            raise ValueError("Could not convert 'max_latency' value of '{}' to an integer".format(timeout))
        if timeout < 0:
            raise ValueError("Invalid negative 'max_latency' value ({})".format(timeout))

        self.id = kwargs.get('id') or str(uuid4())
        self.origin = origin or '{}/{}'.format(os.path.basename(sys.argv[0]), platform.uname()[1])
        self.tags = tags or list()
        self.attributes = kwargs.get('attributes', None) or dict()
        self.event_type = kwargs.get('event_type', kwargs.get('type', None)) or 'Heartbeat'
        self.create_time = create_time or datetime.utcnow()
        self.timeout = timeout
        self.max_latency = max_latency
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
        if self.since.total_seconds() > self.timeout:
            return 'expired'  # aka 'stale'
        elif self.latency > self.max_latency:
            return 'slow'
        else:
            return 'ok'

    @classmethod
    def parse(cls, json: JSON) -> 'Heartbeat':
        if not isinstance(json.get('tags', []), list):
            raise ValueError('tags must be a list')
        if not isinstance(json.get('timeout') if json.get('timeout', None) is not None else 0, int):
            raise ValueError('timeout must be an integer')
        if not isinstance(json.get('attributes', {}), dict):
            raise ValueError('attributes must be a JSON object')
        if json.get('customer', None) == '':
            raise ValueError('customer must not be an empty string')

        return Heartbeat(
            id=json.get('id', None),
            origin=json.get('origin', None),
            tags=json.get('tags', list()),
            attributes=json.get('attributes', dict()),
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
            'attributes': self.attributes,
            'type': self.event_type,
            'createTime': self.create_time,
            'timeout': self.timeout,
            'maxLatency': self.max_latency,
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
            attributes=doc.get('attributes', dict()),
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
            attributes=dict(getattr(rec, 'attributes') or ()),
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
    def find_by_id(id: str, customers: List[str] = None) -> Optional['Heartbeat']:
        return Heartbeat.from_db(db.get_heartbeat(id, customers))

    # search heartbeats
    @staticmethod
    def find_all(query: Query = None) -> List['Heartbeat']:
        return [Heartbeat.from_db(heartbeat) for heartbeat in db.get_heartbeats(query)]

    # delete a heartbeat
    def delete(self) -> bool:
        return db.delete_heartbeat(self.id)
