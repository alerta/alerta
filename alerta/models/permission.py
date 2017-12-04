
from uuid import uuid4

from alerta.app import db
from alerta.utils.api import absolute_url


class Permission(object):

    def __init__(self, match, scopes, **kwargs):

        self.id = kwargs.get('id', str(uuid4()))
        self.match = match
        self.scopes = scopes or list()

    @classmethod
    def parse(cls, json):
        if not isinstance(json.get('scopes', []), list):
            raise ValueError('scopes must be a list')

        return Permission(
            match=json.get('match', None),
            scopes=json.get('scopes', list())
        )

    @property
    def serialize(self):
        return {
            'id': self.id,
            'href': absolute_url('/perm/' + self.id),
            'match': self.match,
            'scopes': self.scopes
        }

    def __repr__(self):
        return 'Perm(id=%r, match=%r, scopes=%r)' % (
            self.id, self.match, self.scopes)

    @classmethod
    def from_document(cls, doc):
        return Permission(
            id=doc.get('id', None) or doc.get('_id'),
            match=doc.get('match', None),
            scopes=doc.get('scopes', list())
        )

    @classmethod
    def from_record(cls, rec):
        return Permission(
            id=rec.id,
            match=rec.match,
            scopes=rec.scopes
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
        return Permission.from_db(db.create_perm(self))

    @staticmethod
    def find_by_id(id):
        return Permission.from_db(db.get_perm(id))

    @staticmethod
    def find_all(query=None):
        return [Permission.from_db(perm) for perm in db.get_perms(query)]

    def delete(self):
        return db.delete_perm(self.id)

    @classmethod
    def is_in_scope(cls, scope, scopes):
        if scope in scopes or scope.split(':')[0] in scopes:
            return True
        elif scope.startswith('read'):
            return cls.is_in_scope(scope.replace('read', 'write'), scopes)
        elif scope.startswith('write'):
            return cls.is_in_scope(scope.replace('write', 'admin'), scopes)
        else:
            return False

    @classmethod
    def lookup(cls, login, groups):
        return db.get_scopes_by_match(login, matches=groups)
