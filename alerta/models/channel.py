from typing import Any, Dict, List, Optional, Tuple, Union
from alerta.app import db


class CustomerChannel:
    def __init__(self, name, channel_type, properties, customer_id, id=None):
        self.id = id
        self.name = name
        self.channel_type = channel_type
        self.properties = properties
        self.customer_id = customer_id

    def create(self):
        return CustomerChannel.from_db(db.create_channel(self))

    @classmethod
    def from_record(cls, rec) -> 'CustomerChannel':
        return CustomerChannel(rec.name, rec.channel_type, rec.properties, rec.customer_id, rec.id)

    @classmethod
    def from_db(cls, r: Union[Dict, Tuple]) -> 'CustomerChannel':
        if isinstance(r, dict):
            return cls.from_document(r)
        elif isinstance(r, tuple):
            return cls.from_record(r)

    @property
    def serialize(self):
        return {
            "id": self.id,
            "name": self.name,
            "channel_type": self.channel_type,
            "properties": self.properties,
            "customer_id": self.customer_id
        }

    @staticmethod
    def find_all(customer_id, sort_by, ascending, limit, offset):
        return [CustomerChannel.from_db(channel) for channel in
                db.get_channels(customer_id, sort_by, ascending, limit, offset)]

    @staticmethod
    def find_by_id(channel_id):
        return CustomerChannel.from_db(db.find_channel_by_id(channel_id))

    @staticmethod
    def update_by_id(channel_id, name=None, properties=None, **kwargs):
        return CustomerChannel.from_db(db.update_channel_by_id(channel_id, name, properties))

    @staticmethod
    def delete_by_id(channel_id):
        return CustomerChannel.from_db(db.delete_channel_by_id(channel_id))
