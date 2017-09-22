
from datetime import datetime, timedelta
from uuid import uuid4

from alerta.app import db, qb, key_helper
from alerta.utils.api import absolute_url
from alerta.utils.format import DateTime


class ApiKey(object):

    def __init__(self, user, scopes, text='', expire_time=None, customer=None, **kwargs):

        self.id = kwargs.get('id', None) or str(uuid4())
        self.key = kwargs.get('key', key_helper.generate())
        self.user = user
        self.scopes = scopes or key_helper.user_default_scopes
        self.text = text
        self.expire_time = expire_time or datetime.utcnow() + timedelta(days=key_helper.api_key_expire_days)
        self.count = kwargs.get('count', 0)
        self.last_used_time = kwargs.get('last_used_time', None)
        self.customer = customer

    @property
    def type(self):
        return key_helper.scopes_to_type(self.scopes)

    @classmethod
    def parse(cls, json):
        if not isinstance(json.get('scopes', []), list):
            raise ValueError('scopes must be a list')

        api_key = ApiKey(
            user=json.get('user', None),
            scopes=json.get('scopes', None) or list(),
            text=json.get('text', None),
            expire_time=DateTime.parse(json.get('expireTime')),
            customer=json.get('customer', None)
        )
        if 'type' in json:
            api_key.scopes = key_helper.type_to_scopes(api_key.user, json['type'])

        return api_key

    @property
    def serialize(self):
        return {
            'id': self.id,
            'key': self.key,
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

    def __repr__(self):
        return 'ApiKey(key=%r, user=%r, scopes=%r, expireTime=%r, customer=%r)' % (
            self.key, self.user, self.scopes, self.expire_time, self.customer)

    @classmethod
    def from_document(cls, doc):
        return ApiKey(
            id=doc.get('id', None) or doc.get('_id'),
            key=doc.get('key', None) or doc.get('_id'),
            user=doc.get('user', None),
            scopes=doc.get('scopes', None) or key_helper.type_to_scopes(doc.get('user', None), doc.get('type', None)) or list(),
            text=doc.get('text', None),
            expire_time=doc.get('expireTime', None),
            count=doc.get('count', None),
            last_used_time=doc.get('lastUsedTime', None),
            customer=doc.get('customer', None)
        )

    @classmethod
    def from_record(cls, rec):
        return ApiKey(
            id=rec.id,
            key=rec.key,
            user=rec.user,
            scopes=rec.scopes,  # legacy type => scopes conversion only required for mongo documents
            text=rec.text,
            expire_time=rec.expire_time,
            count=rec.count,
            last_used_time=rec.last_used_time,
            customer=rec.customer
        )

    @classmethod
    def from_db(cls, r):
        if isinstance(r, dict):
            return cls.from_document(r)
        elif isinstance(r, tuple):
            return cls.from_record(r)
        else:
            return

    def create(self):
        """
        Create a new API key.
        """
        return ApiKey.from_db(db.create_key(self))

    @staticmethod
    def get(key):
        """
        Get API key details.
        """
        return ApiKey.from_db(db.get_key(key))

    @staticmethod
    def find_all(query=None):
        """
        List all API keys.
        """
        return [ApiKey.from_db(key) for key in db.get_keys(query)]

    @staticmethod
    def find_by_user(user):
        """
        List API keys for a user.
        """
        return [ApiKey.from_db(key) for key in db.get_keys(qb.from_dict({"user": user}))]

    def delete(self):
        """
        Delete an API key.
        """
        return db.delete_key(self.key)

    @staticmethod
    def verify_key(key):
        key_info = ApiKey.from_db(db.get_key(key))
        if key_info and key_info.expire_time > datetime.utcnow():
            db.update_key_last_used(key)
            return key_info
