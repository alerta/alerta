import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import validators

from alerta.app import db

JSON = Dict[str, Any]


class SuppressionRule:
    def __init__(self, name, rules, is_active=True, id=None):
        self.name = name
        self.rules = rules
        self.is_active = is_active
        self.id = id

    def create(self):
        return SuppressionRule.from_db(db.create_suppression_rule(self))

    def validate(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise Exception("Suppression rule name must be a valid text value")
        if not isinstance(self.rules, list):
            raise Exception("Suppression rule properties must be valid to create a suppression rule")
        if not isinstance(self.is_active, bool):
            raise Exception("Suppression rule is_active flag must be true or false")

    @classmethod
    def from_record(cls, rec) -> 'SuppressionRule':
        return SuppressionRule(rec.name, rec.rules, rec.is_active, rec.id)

    @classmethod
    def from_db(cls, r: Union[Dict, Tuple]) -> 'SuppressionRule':
        if isinstance(r, dict):
            return cls.from_document(r)
        elif isinstance(r, tuple):
            return cls.from_record(r)

    @classmethod
    def parse(cls, json: JSON) -> 'SuppressionRule':
        if not isinstance(json.get('name'), str) or json.get('name').strip() == "":
            raise Exception("Suppression rule name is required, it must be a string")
        if not isinstance(json.get('rules'), list):
            raise Exception("Suppression rule properties are required")
        return SuppressionRule(**json)

    @property
    def serialize(self):
        return {
            "id": self.id,
            "name": self.name,
            "rules": self.rules,
            "is_active": self.is_active
        }
