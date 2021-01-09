from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

from alerta.app import db, key_helper
from alerta.database.base import Query
from alerta.models.enums import Scope
from alerta.utils.format import DateTime
from alerta.utils.response import absolute_url

JSON = Dict[str, Any]


class ApiKeyStatus(str, Enum):

    Active = 'active'
    Expired = 'expired'


class ApiKey:

    def __init__(self, user: str, scopes: List[Scope], text: str = '', expire_time: datetime = None, customer: str = None, **kwargs) -> None:

        self.id = kwargs.get('id') or str(uuid4())
        self.key = kwargs.get('key', None) or key_helper.generate()
        self.user = user
        self.scopes = scopes or key_helper.user_default_scopes
        self.text = text
        self.expire_time = expire_time or datetime.utcnow() + timedelta(days=key_helper.api_key_expire_days)
        self.count = kwargs.get('count', 0)
        self.last_used_time = kwargs.get('last_used_time', None)
        self.customer = customer

    @property
    def type(self) -> str:
        return key_helper.scopes_to_type(self.scopes)

    @property
    def status(self) -> ApiKeyStatus:
        return ApiKeyStatus.Expired if datetime.utcnow() > self.expire_time else ApiKeyStatus.Active

    @classmethod
    def parse(cls, json: JSON) -> 'ApiKey':
        if not isinstance(json.get('scopes', []), list):
            raise ValueError('scopes must be a list')

        api_key = ApiKey(
            id=json.get('id', None),
            user=json.get('user', None),
            scopes=[Scope(s) for s in json.get('scopes', [])],
            text=json.get('text', None),
            expire_time=DateTime.parse(json['expireTime']) if 'expireTime' in json else None,
            customer=json.get('customer', None)
        )
        if 'type' in json:
            api_key.scopes = key_helper.type_to_scopes(api_key.user, json['type'])

        return api_key

    @property
    def serialize(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'key': self.key,
            'status': self.status,
            'href': absolute_url('/key/' + self.key),
            'user': self.user,
            'scopes': self.scopes,
            'type': self.type,
            'text': self.text,
            'expireTime': self.expire_time,
            'count': self.count,
            'lastUsedTime': self.last_used_time,
            'customer': self.customer
        }

    def __repr__(self) -> str:
        return 'ApiKey(key={!r}, status={!r}, user={!r}, scopes={!r}, expireTime={!r}, customer={!r})'.format(
            self.key, self.status, self.user, self.scopes, self.expire_time, self.customer)

    @classmethod
    def from_document(cls, doc: Dict[str, Any]) -> 'ApiKey':
        return ApiKey(
            id=doc.get('id', None) or doc.get('_id'),
            key=doc.get('key', None) or doc.get('_id'),
            user=doc.get('user', None),
            scopes=[Scope(s) for s in doc.get('scopes', list())] or key_helper.type_to_scopes(
                doc.get('user', None), doc.get('type', None)) or list(),
            text=doc.get('text', None),
            expire_time=doc.get('expireTime', None),
            count=doc.get('count', None),
            last_used_time=doc.get('lastUsedTime', None),
            customer=doc.get('customer', None)
        )

    @classmethod
    def from_record(cls, rec) -> 'ApiKey':
        return ApiKey(
            id=rec.id,
            key=rec.key,
            user=rec.user,
            scopes=[Scope(s) for s in rec.scopes],  # legacy type => scopes conversion only required for mongo documents
            text=rec.text,
            expire_time=rec.expire_time,
            count=rec.count,
            last_used_time=rec.last_used_time,
            customer=rec.customer
        )

    @classmethod
    def from_db(cls, r: Union[Dict, Tuple]) -> 'ApiKey':
        if isinstance(r, dict):
            return cls.from_document(r)
        elif isinstance(r, tuple):
            return cls.from_record(r)

    def create(self) -> 'ApiKey':
        """
        Create a new API key.
        """
        return ApiKey.from_db(db.create_key(self))

    @staticmethod
    def find_by_id(key: str, user: str = None) -> Optional['ApiKey']:
        """
        Get API key details.
        """
        return ApiKey.from_db(db.get_key(key, user))

    @staticmethod
    def find_all(query: Query = None, page: int = 1, page_size: int = 1000) -> List['ApiKey']:
        """
        List all API keys.
        """
        return [ApiKey.from_db(key) for key in db.get_keys(query, page, page_size)]

    @staticmethod
    def count(query: Query = None) -> int:
        return db.get_keys_count(query)

    @staticmethod
    def find_by_user(user: str) -> List['ApiKey']:
        """
        List API keys for a user.
        """
        return [ApiKey.from_db(key) for key in db.get_keys_by_user(user)]

    def update(self, **kwargs) -> 'ApiKey':
        kwargs['expireTime'] = DateTime.parse(kwargs['expireTime']) if 'expireTime' in kwargs else None
        return ApiKey.from_db(db.update_key(self.key, **kwargs))

    def delete(self) -> bool:
        """
        Delete an API key.
        """
        return db.delete_key(self.key)

    @staticmethod
    def verify_key(key: str) -> Optional['ApiKey']:
        key_info = ApiKey.from_db(db.get_key(key))
        if key_info and key_info.expire_time > datetime.utcnow():
            db.update_key_last_used(key)
            return key_info
        return None
