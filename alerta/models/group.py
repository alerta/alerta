from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

from alerta.app import db
from alerta.database.base import Query
from alerta.utils.response import absolute_url

JSON = Dict[str, Any]


class GroupUser:

    def __init__(self, id: str, login: str, name: str, status: str) -> None:
        self.id = id
        self.login = login
        self.name = name
        self.status = status

    @property
    def serialize(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'href': absolute_url('/user/' + self.id),
            'login': self.login,
            'name': self.name,
            'status': self.status
        }

    @classmethod
    def from_document(cls, doc: Dict[str, Any]) -> 'GroupUser':
        return GroupUser(
            id=doc.get('id', None),
            name=doc.get('name', None),
            login=doc.get('login', None) or doc.get('email', None),
            status=doc.get('status', None)
        )

    @classmethod
    def from_record(cls, rec):
        return GroupUser(
            id=rec.id,
            login=(rec.login or rec.email),
            name=rec.name,
            status=rec.status
        )

    @classmethod
    def from_db(cls, r):
        if isinstance(r, dict):
            return cls.from_document(r)
        elif isinstance(r, tuple):
            return cls.from_record(r)


class GroupUsers:

    def __init__(self, id: str, users: List[GroupUser]) -> None:
        self.id = id
        self.users = users

    @staticmethod
    def find_by_id(id: str) -> List['GroupUser']:
        return [GroupUser.from_db(user) for user in db.get_group_users(id)]


class Group:
    """
    Group model.
    """

    def __init__(self, name: str, text: str, **kwargs) -> None:
        if not name:
            raise ValueError('Missing mandatory value for name')

        self.id = kwargs.get('id') or str(uuid4())
        self.name = name
        self.text = text or ''
        self.count = kwargs.get('count')

    @classmethod
    def parse(cls, json: JSON) -> 'Group':
        return Group(
            id=json.get('id', None),
            name=json.get('name', None),
            text=json.get('text', None)
        )

    @property
    def serialize(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'href': absolute_url('/group/' + self.id),
            'name': self.name,
            'text': self.text,
            'count': self.count
        }

    def __repr__(self) -> str:
        return 'Group(id={!r}, name={!r}, text={!r}, count={!r})'.format(
            self.id, self.name, self.text, self.count)

    @classmethod
    def from_document(cls, doc: Dict[str, Any]) -> 'Group':
        return Group(
            id=doc.get('id', None) or doc.get('_id'),
            name=doc.get('name', None),
            text=doc.get('text', None),
            count=len(doc.get('users', []))
        )

    @classmethod
    def from_record(cls, rec) -> 'Group':
        return Group(
            id=rec.id,
            name=rec.name,
            text=rec.text,
            count=len(rec.users or [])
        )

    @classmethod
    def from_db(cls, r: Union[Dict, Tuple]) -> 'Group':
        if isinstance(r, dict):
            return cls.from_document(r)
        elif isinstance(r, tuple):
            return cls.from_record(r)

    def create(self) -> 'Group':
        return Group.from_db(db.create_group(self))

    @staticmethod
    def find_by_id(id: str) -> Optional['Group']:
        return Group.from_db(db.get_group(id))

    @staticmethod
    def find_all(query: Query = None) -> List['Group']:
        return [Group.from_db(group) for group in db.get_groups(query)]

    def update(self, **kwargs) -> 'Group':
        return Group.from_db(db.update_group(self.id, **kwargs))

    def add_user(self, user_id):
        return db.add_user_to_group(group=self.id, user=user_id)

    def remove_user(self, user_id):
        return db.remove_user_from_group(group=self.id, user=user_id)

    def delete(self) -> bool:
        return db.delete_group(self.id)
