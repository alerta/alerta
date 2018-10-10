from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

from alerta.app import db
from alerta.database.base import Query
from alerta.utils.response import absolute_url

JSON = Dict[str, Any]


class Permission:

    def __init__(self, match: str, scopes: List[str], **kwargs) -> None:

        self.id = kwargs.get('id', str(uuid4()))
        self.match = match
        self.scopes = scopes or list()

    @classmethod
    def parse(cls, json: JSON) -> 'Permission':
        if not isinstance(json.get('scopes', []), list):
            raise ValueError('scopes must be a list')

        return Permission(
            match=json.get('match', None),
            scopes=json.get('scopes', list())
        )

    @property
    def serialize(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'href': absolute_url('/perm/' + self.id),
            'match': self.match,
            'scopes': self.scopes
        }

    def __repr__(self) -> str:
        return 'Perm(id={!r}, match={!r}, scopes={!r})'.format(
            self.id, self.match, self.scopes)

    @classmethod
    def from_document(cls, doc: Dict[str, Any]) -> 'Permission':
        return Permission(
            id=doc.get('id', None) or doc.get('_id'),
            match=doc.get('match', None),
            scopes=doc.get('scopes', list())
        )

    @classmethod
    def from_record(cls, rec) -> 'Permission':
        return Permission(
            id=rec.id,
            match=rec.match,
            scopes=rec.scopes
        )

    @classmethod
    def from_db(cls, r: Union[Dict, Tuple]) -> 'Permission':
        if isinstance(r, dict):
            return cls.from_document(r)
        elif isinstance(r, tuple):
            return cls.from_record(r)

    def create(self) -> 'Permission':
        return Permission.from_db(db.create_perm(self))

    @staticmethod
    def find_by_id(id: str) -> Optional['Permission']:
        return Permission.from_db(db.get_perm(id))

    @staticmethod
    def find_all(query: Query=None) -> List['Permission']:
        return [Permission.from_db(perm) for perm in db.get_perms(query)]

    def delete(self) -> bool:
        return db.delete_perm(self.id)

    @classmethod
    def is_in_scope(cls, scope: str, scopes: List[str]) -> bool:
        if scope in scopes or scope.split(':')[0] in scopes:
            return True
        elif scope.startswith('read'):
            return cls.is_in_scope(scope.replace('read', 'write'), scopes)
        elif scope.startswith('write'):
            return cls.is_in_scope(scope.replace('write', 'admin'), scopes)
        else:
            return False

    @classmethod
    def lookup(cls, login: str, groups: List[str]) -> List[str]:
        return db.get_scopes_by_match(login, matches=groups)
