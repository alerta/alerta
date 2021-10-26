from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

from alerta.app import db
from alerta.database.base import Query
from alerta.utils.response import absolute_url

JSON = Dict[str, Any]


class Rule:

    def __init__(self, customer_id: str, is_active: bool, name: str, rules: dict, id=None, **kwargs) -> None:
        self.id = id
        self.customer_id = customer_id
        self.is_active = is_active
        self.rules = rules
        self.name = name

    @classmethod
    def parse(cls, json: JSON) -> 'Rule':
        return Rule(
            id=json.get('id', None),
            customer_id=json.get('customer_id', None),
            is_active=json.get('is_active', False),
            rules=json.get('rules', None),
            name=json.get('name', None)
        )

    @property
    def serialize(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'href': absolute_url(f'/rule/{self.id}'),
            'customer_id': self.customer_id,
            'is_active': self.is_active,
            'rules': self.rules,
            'name': self.name
        }

    def __repr__(self) -> str:
        return f"Rule(id={self.id}, customer_id={self.customer_id}, is_active={self.is_active})"

    @classmethod
    def from_document(cls, doc: Dict[str, Any]) -> 'Rule':
        return Rule(
            id=doc.get('id', None) or doc.get('_id'),
            customer_id=doc.get('customer_id', None),
            is_active=doc.get('is_active', None),
            rules=doc.get('rules', None),
            name=doc.get('name', None)
        )

    @classmethod
    def from_record(cls, rec) -> 'Rule':
        return Rule(
            id=rec.id,
            customer_id=rec.customer_id,
            rules=rec.rules,
            is_active=rec.is_active,
            name=rec.name
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
    def find_by_id(id: int, customer_id: str) -> Optional['Rule']:
        return Rule.from_db(db.get_rule(id, customer_id))

    @staticmethod
    def find_all(customer_id, sort_by='id', ascending=True, limit=10, offset=0) -> List['Rule']:
        return [Rule.from_db(rule) for rule in db.get_rules(customer_id, sort_by, ascending, limit, offset)]

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

    @staticmethod
    def update_by_id(rule_id, customer_id, **kwargs):
        return Rule.from_db(db.update_rule_by_id(rule_id, customer_id, **kwargs))

    @staticmethod
    def delete_by_id(rule_id, customer_id):
        return Rule.from_db(db.delete_by_id(rule_id, customer_id))
