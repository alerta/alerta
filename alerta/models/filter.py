from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

from alerta.app import db
from alerta.database.base import Query
from alerta.utils.response import absolute_url

JSON = Dict[str, Any]


class Filter:

    def __init__(self, environment: str, **kwargs) -> None:
        if not environment:
            raise ValueError('Missing mandatory value for "environment"')
        if not kwargs.get('type'):
            raise ValueError('Missing mandatory value for "type"')
        if any(['.' in key for key in kwargs.get('attributes', dict()).keys()]) \
                or any(['$' in key for key in kwargs.get('attributes', dict()).keys()]):
            raise ValueError('attributes keys must not contain "." or "$"')

        self.id = kwargs.get('id') or str(uuid4())
        self.environment = environment
        self.service = kwargs.get('service', None) or list()
        self.resource = kwargs.get('resource', None)
        self.event = kwargs.get('event', None)
        self.group = kwargs.get('group', None)
        self.tags = kwargs.get('tags', None) or list()
        self.origin = kwargs.get('origin', None)
        self.customer = kwargs.get('customer', None)
        self.type = kwargs.get('type')
        self.attributes = kwargs.get('attributes', None) or dict()

        self.user = kwargs.get('user', None)
        self.create_time = kwargs['create_time'] if 'create_time' in kwargs else datetime.utcnow()
        self.text = kwargs.get('text', None)

    @classmethod
    def parse(cls, json: JSON) -> 'Filter':
        if not isinstance(json.get('service', []), list):
            raise ValueError('service must be a list')
        if not isinstance(json.get('tags', []), list):
            raise ValueError('tags must be a list')
        if not isinstance(json.get('attributes', {}), dict):
            raise ValueError('attributes must be a JSON object')

        return Filter(
            id=json.get('id', None),
            environment=json['environment'],
            service=json.get('service', list()),
            resource=json.get('resource', None),
            event=json.get('event', None),
            group=json.get('group', None),
            tags=json.get('tags', list()),
            origin=json.get('origin', None),
            customer=json.get('customer', None),
            type=json.get('type'),
            attributes=json.get('attributes', dict()),
            user=json.get('user', None),
            text=json.get('text', None)
        )

    @classmethod
    def validate_inputs(cls, json: JSON) -> 'Filter':
        if 'environment' in json:
            if not isinstance(json.get('environment'), str):
                raise ValueError("'environment' must be string")

        if 'resource' in json:
            if not isinstance(json.get('resource'), (str, type(None))):
                raise ValueError("'resource' must be a string")

        if 'service' in json:
            if not isinstance(json.get('service'), (list, type(None))):
                raise ValueError("'service' must be a list")

        if 'event' in json:
            if not isinstance(json.get('event'), (str, type(None))):
                raise ValueError("'event' must be a string")

        if 'group' in json:
            if not isinstance(json.get('group'), (str, type(None))):
                raise ValueError("'group' must be a string")

        if 'tags' in json:
            if not isinstance(json.get('tags'), (list, type(None))):
                raise ValueError("'tags' must be a list")

        if 'type' in json:
            if not isinstance(json.get('type'), str):
                raise ValueError("'type' must be string")

        if 'attributes' in json:
            if not isinstance(json.get('attributes'), (dict, type(None))):
                raise ValueError("'attributes' must be a JSON object")

        return True

    @property
    def serialize(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'href': absolute_url('/filter/' + self.id),
            'environment': self.environment,
            'service': self.service,
            'resource': self.resource,
            'event': self.event,
            'group': self.group,
            'tags': self.tags,
            'origin': self.origin,
            'customer': self.customer,
            'type': self.type,
            'attributes': self.attributes,
            'user': self.user,
            'createTime': self.create_time,
            'text': self.text
        }

    def __repr__(self) -> str:
        more = ''
        if self.service:
            more += f'service={self.service!r}, '
        if self.resource:
            more += f'resource={self.resource!r}, '
        if self.event:
            more += f'event={self.event!r}, '
        if self.group:
            more += f'group={self.group!r}, '
        if self.tags:
            more += f'tags={self.tags!r}, '
        if self.origin:
            more += f'origin={self.origin!r}, '
        if self.customer:
            more += f'customer={self.customer!r}, '

        return 'Filter(id={!r}, environment={!r}, {}type={!r}, attributes={!r})'.format(
            self.id,
            self.environment,
            more,
            self.type,
            self.attributes,
        )

    @classmethod
    def from_document(cls, doc: Dict[str, Any]) -> 'Filter':
        return Filter(
            id=doc.get('id', None) or doc.get('_id'),
            environment=doc['environment'],
            service=doc.get('service', list()),
            resource=doc.get('resource', None),
            event=doc.get('event', None),
            group=doc.get('group', None),
            tags=doc.get('tags', list()),
            origin=doc.get('origin'),
            customer=doc.get('customer', None),
            type=doc.get('type'),
            attributes=doc.get('attributes', dict()),
            user=doc.get('user', None),
            create_time=doc.get('createTime', None),
            text=doc.get('text', None)
        )

    @classmethod
    def from_record(cls, rec) -> 'Filter':
        return Filter(
            id=rec.id,
            environment=rec.environment,
            service=rec.service,
            resource=rec.resource,
            event=rec.event,
            group=rec.group,
            tags=rec.tags,
            origin=rec.origin,
            customer=rec.customer,
            type=rec.type,
            attributes=dict(rec.attributes),
            user=rec.user,
            create_time=rec.create_time,
            text=rec.text
        )

    @classmethod
    def from_db(cls, r: Union[Dict, Tuple]) -> 'Filter':
        if isinstance(r, dict):
            return cls.from_document(r)
        elif isinstance(r, tuple):
            return cls.from_record(r)

    # create a filter
    def create(self) -> 'Filter':
        return Filter.from_db(db.create_filter(self))

    # get a filter
    @staticmethod
    def find_by_id(id: str, customers: List[str] = None) -> Optional['Filter']:
        return Filter.from_db(db.get_filter(id, customers))

    @staticmethod
    def find_all(query: Query = None, page: int = 1, page_size: int = 1000) -> List['Filter']:
        return [Filter.from_db(filter) for filter in db.get_filters(query, page, page_size)]

    @staticmethod
    def find_matching_filters(self, type: str) -> List['Filter']:
        """Does this alert match a filter"""
        return [Filter.from_db(filter) for filter in db.get_matching_filters_by_type(self, type)]

    @staticmethod
    def count(query: Query = None) -> int:
        return db.get_filters_count(query)

    # get types
    @staticmethod
    def get_types(query: Query = None) -> List[str]:
        return db.get_filter_types(query)

    def update(self, **kwargs) -> 'Filter':
        return Filter.from_db(db.update_filter(self.id, **kwargs))

    def delete(self) -> bool:
        return db.delete_filter(self.id)
