import json
import re
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
        if not isinstance(json.get('customer_id'), str) or json.get('customer_id').strip() == "":
            raise Exception("customer_id is required, it must be a string")
        if not isinstance(json.get('is_active'), bool):
            raise Exception("is_active is required, it must be a boolean")
        if not isinstance(json.get('rules'), list):
            raise Exception("rules is required, it must be a list")
        if not isinstance(json.get('name'), str) or json.get('name').strip() == "":
            raise Exception("name is required, it must be a string")
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
            rules=[json.loads(s) for s in rec.rules],
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
        self.validate()
        return Rule.from_db(db.create_rule(self))

    def validate(self):
        if self.name.strip() == "":
            raise Exception("Rule-name must be a name string")
        if not isinstance(self.is_active, bool):
            raise Exception("is_active must be either true or false")
        if len(self.rules) == 0:
            raise Exception("Rules expects 'rules' property to be passed, a list of fields")
        for rule in self.rules:
            fields = rule.get('fields')
            if not isinstance(fields, list):
                raise Exception("Fields property under rules list must be a list of field,regex values")
            for _field in fields:
                if not isinstance(_field, dict):
                    raise Exception("fields must be of format \"{'field':'field_name','regex':'regex_value'}\"")
                field, regex = _field.get("field", ""), _field.get("regex", "")
                if not field or not field.strip():
                    raise Exception("Supported fields are resource, event, tags, severity")
                if not regex or not regex.strip():
                    raise Exception("Regex value cannot be empty")
                try:
                    re.compile(regex)
                except Exception as e:
                    raise Exception("Regex value is an invalid one, please verify the regex you've passed")

    @staticmethod
    def find_by_id(id: int, customer_id: str) -> Optional['Rule']:
        value = db.get_customer_rules_count(customer_id)
        if value.count == 0:
            raise Exception(f'customer with id {customer_id} not found')
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
    def update_by_id(rule_id, customer_id, rules=None, is_active=None, name=None):
        rule = Rule.find_by_id(rule_id, customer_id)
        if not rule:
            raise Exception(f"rule with id {rule_id} not found")
        if isinstance(rules, list):
            rule.rules = rules
        if isinstance(is_active, bool):
            rule.is_active = is_active
        if isinstance(name, str):
            rule.name = name
        rule.validate()
        return Rule.from_db(db.update_rule_by_id(rule_id, customer_id, rules=rules, is_active=is_active, name=name))

    @staticmethod
    def delete_by_id(rule_id, customer_id):
        try:
            return Rule.from_db(db.delete_by_id(rule_id, customer_id))
        except Exception as e:
            if 'violates foreign key constraint' in str(e):
                raise Exception('cannot delete rule, rule has reference in channel-rule-map')
            raise e
