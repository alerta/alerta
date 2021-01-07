from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

from flask import current_app

from alerta.app import db
from alerta.database.base import Query
from alerta.models.enums import Scope
from alerta.utils.response import absolute_url

JSON = Dict[str, Any]


class Permission:

    def __init__(self, match: str, scopes: List[Scope], **kwargs) -> None:

        self.id = kwargs.get('id') or str(uuid4())
        self.match = match
        self.scopes = scopes or list()

    @classmethod
    def parse(cls, json: JSON) -> 'Permission':
        if not isinstance(json.get('scopes', []), list):
            raise ValueError('scopes must be a list')

        return Permission(
            id=json.get('id', None),
            match=json.get('match', None),
            scopes=[Scope(s) for s in json.get('scopes', list())]
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
            scopes=[Scope(s) for s in doc.get('scopes', list())]
        )

    @classmethod
    def from_record(cls, rec) -> 'Permission':
        return Permission(
            id=rec.id,
            match=rec.match,
            scopes=[Scope(s) for s in rec.scopes]
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
    def find_all(query: Query = None, page: int = 1, page_size: int = 1000) -> List['Permission']:
        return [Permission.from_db(perm) for perm in db.get_perms(query, page, page_size)]

    @staticmethod
    def count(query: Query = None) -> int:
        return db.get_perms_count(query)

    def update(self, **kwargs) -> 'Permission':
        return Permission.from_db(db.update_perm(self.id, **kwargs))

    def delete(self) -> bool:
        return db.delete_perm(self.id)

    @classmethod
    def is_in_scope(cls, want_scope: str, have_scopes: List[Scope]) -> bool:
        """Return True if wanted scope is in list of scopes or derived scopes.

        :param want_scope: scope wanted for permission to do something (str because could be invalid scope)
        :param have_scopes: list of valid scopes that user has been assigned
        """
        if not want_scope:
            return True
        if want_scope in have_scopes or want_scope.split(':')[0] in have_scopes:
            return True
        elif want_scope.startswith('read'):
            return cls.is_in_scope(want_scope.replace('read', 'write'), have_scopes)
        elif want_scope.startswith('write'):
            return cls.is_in_scope(want_scope.replace('write', 'admin'), have_scopes)
        elif want_scope.startswith('delete'):
            if want_scope in current_app.config['DELETE_SCOPES']:
                return cls.is_in_scope(want_scope.replace('delete', 'admin'), have_scopes)
            else:
                return cls.is_in_scope(want_scope.replace('delete', 'write'), have_scopes)
        else:
            return False

    @classmethod
    def lookup(cls, login: str, roles: List[str]) -> List[Scope]:
        return [Scope(s) for s in db.get_scopes_by_match(login, matches=roles)]
