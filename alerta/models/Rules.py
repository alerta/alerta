from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

from alerta.app import db
from alerta.database.base import Query
from alerta.utils.response import absolute_url

JSON = Dict[str, Any]


class Rule:

    def __init__(self, id: str, customer_id: str, is_active: bool, rules: dict, **kwargs) -> None:
        self.id = id
        self.customer_id = customer_id
        self.is_active = is_active
        self.rules = rules

    @classmethod
    def parse(cls, json: JSON) -> 'Rule':
        return Rule(
            id=json.get('id', None),
            customer_id=json.get('customer_id', None),
            is_active=json.get('is_active', False),
            rules=json.get('rules', None)
        )

    @property
    def serialize(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'href': absolute_url('/rule/' + self.id),
            'customer_id': self.customer_id,
            'is_active': self.is_active,
            'rules': self.rules
        }

    def __repr__(self) -> str:
        # return 'Rule(id={rul}, customer_id={},)'.format(
        #     self.id, self.match, self.customer)
        return f"Rule(id={self.id}, customer_id={self.customer_id}, is_active={self.is_active})"

    @classmethod
    def from_document(cls, doc: Dict[str, Any]) -> 'Rule':
        return Rule(
            id=doc.get('id', None) or doc.get('_id'),
            customer_id=doc.get('customer_id', None),
            is_active=doc.get('is_active', None),
            rules=doc.get('rules', None)
        )

    @classmethod
    def from_record(cls, rec) -> 'Rule':
        return Rule(
            id=rec.id,
            customer_id=rec.customer_id,
            rules=rec.rules,
            is_active=rec.is_active
        )

    @classmethod
    def from_db(cls, r: Union[Dict, Tuple]) -> 'Rule':
        if isinstance(r, dict):
            return cls.from_document(r)
        elif isinstance(r, tuple):
            return cls.from_record(r)

    def create(self) -> 'Rule':
        return Rule.from_db(db.create_rule(self))

    @staticmethod
    def find_by_id(id: str) -> Optional['Rule']:
        return Rule.from_db(db.get_rule(id))

    @staticmethod
    def find_all(query: Query = None, page: int = 1, page_size: int = 1000) -> List['Rule']:
        return [Rule.from_db(rule) for rule in db.get_rules(query, page, page_size)]

    @staticmethod
    def count(query: Query = None) -> int:
        return db.get_rules_count(query)

    def update(self, **kwargs) -> 'Rule':
        return Rule.from_db(db.update_rule(self.id, **kwargs))

    def delete(self) -> bool:
        return db.delete_rule(self.id)

    @classmethod
    def lookup(cls, login: str, groups: List[str]) -> List[str]:
        # rules = db.get_rules_by_match(login, matches=groups)
        # return rules if rules != '*' else []
        raise NotImplementedError()
