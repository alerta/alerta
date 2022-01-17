from typing import Tuple, Dict, Union

from alerta.app import db
from alerta.models.alert import Alert


class CustomerChannelRuleMap:
    def __init__(self, channel_id, rule_id, id=None):
        self.channel_id = channel_id
        self.rule_id = rule_id
        self.id = id

    def create(self):
        return CustomerChannelRuleMap.from_db(db.create_customer_rule_map(self))

    @classmethod
    def from_record(cls, rec) -> 'CustomerChannelRuleMap':
        return CustomerChannelRuleMap(rec.channel_id, rec.rule_id, rec.id)

    @classmethod
    def from_db(cls, r: Union[Dict, Tuple]) -> 'CustomerChannelRuleMap':
        if isinstance(r, dict):
            return cls.from_document(r)
        elif isinstance(r, tuple):
            return cls.from_record(r)

    @property
    def serialize(self):
        return {
            "id": self.id,
            "channel_id": self.channel_id,
            "rule_id": self.channel_id
        }

    @staticmethod
    def delete_by_id(customer_id, channel_rule_map_id):
        return CustomerChannelRuleMap.from_db(db.delete_customer_rule_map_by_id(customer_id, channel_rule_map_id))

    @staticmethod
    def get_channel_rules(customer_id):
        return [CustomerChannelRuleMap.from_db(r) for r in
                db.get_customer_channel_rule_maps_by_customer_id(customer_id)]
