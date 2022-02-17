import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import validators

from alerta.app import db

JSON = Dict[str, Any]


class CustomerChannel:
    SUPPORTED_CHANNEL_TYPES = ["webhook", "email"]

    def __init__(self, name, channel_type, properties, customer_id, is_active=True, id=None):
        self.id = id
        self.name = name
        self.channel_type = channel_type
        self.properties = properties
        self.customer_id = customer_id
        self.is_active = is_active

    def create(self):
        self.validate()
        return CustomerChannel.from_db(db.create_channel(self))

    def validate(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise Exception("Channel name must be a valid text value")
        if self.channel_type not in CustomerChannel.SUPPORTED_CHANNEL_TYPES:
            raise Exception(f"Support channel types are {CustomerChannel.SUPPORTED_CHANNEL_TYPES}")
        if not isinstance(self.properties, dict):
            raise Exception("Channel properties are required to create channel")
        if self.channel_type == "email":
            emails = self.properties.get("emails", [])
            if not isinstance(emails, list) or len(emails) == 0:
                raise Exception("Emails property must be list of emails")
            for index, email in enumerate(emails):
                if not validators.email(email or ''):
                    raise Exception(f"Email value at position {index + 1} is not valid")
        elif self.channel_type == "webhook":
            url = self.properties.get('url', '')
            if not validators.url(url or ''):
                raise Exception("Webhook property 'url' is required and cannot be empty")

    @classmethod
    def from_record(cls, rec) -> 'CustomerChannel':
        return CustomerChannel(rec.name, rec.channel_type, rec.properties, rec.customer_id, rec.is_active, rec.id)

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
            "customer_id": self.customer_id,
            "is_active": self.is_active,
        }

    @staticmethod
    def find_all(customer_id, sort_by, ascending, limit, offset):
        return [CustomerChannel.from_db(channel) for channel in
                db.get_channels(customer_id, sort_by, ascending, limit, offset)]

    @staticmethod
    def find_by_id(customer_id, channel_id):
        return CustomerChannel.from_db(db.find_channel_by_id(customer_id, channel_id))

    @staticmethod
    def update_by_id(customer_id, channel_id, name=None, properties=None, is_active=None, **kwargs):
        customer_channel = CustomerChannel.find_by_id(customer_id, channel_id)
        if not customer_channel:
            raise Exception("not found")
        if name:
            customer_channel.name = name
        if properties:
            customer_channel.properties = properties
        if isinstance(is_active, bool):
            customer_channel.is_active = is_active
        customer_channel.validate()
        return CustomerChannel.from_db(db.update_channel_by_id(customer_id, channel_id, name, properties, is_active))

    @staticmethod
    def delete_by_id(customer_id, channel_id):
        try:
            return CustomerChannel.from_db(db.delete_channel_by_id(customer_id, channel_id))
        except Exception as e:
            if 'violates foreign key constraint' in str(e):
                raise Exception('cannot delete channel, channel has reference in channel-rule-map')
            raise e

    @classmethod
    def parse(cls, json: JSON) -> 'CustomerChannel':
        if not isinstance(json.get('name'), str) or json.get('name').strip() == "":
            raise Exception("Channel name is required, it must be a string")
        if json.get('channel_type') not in CustomerChannel.SUPPORTED_CHANNEL_TYPES:
            raise Exception(f"Channel type must be one of {CustomerChannel.SUPPORTED_CHANNEL_TYPES}")
        if not isinstance(json.get('properties'), dict):
            raise Exception("Channel properties are required")
        if not isinstance(json.get('customer_id'), str) or json.get('customer_id').strip() == "":
            raise Exception("customer_id is required, it must be a string")
        return CustomerChannel(**json)

    @staticmethod
    def create_admin_email_channel(customer_id, email):
        channel = CustomerChannel('Email channel of the admin', 'email', {'emails': [email]},
                                  customer_id)
        db.create_system_added_channel(channel)


class DeveloperChannel:
    SUPPORTED_CHANNEL_TYPES = ["webhook", "email"]

    def __init__(self, name, channel_type, properties, is_active=True, id=None):
        self.id = id
        self.name = name
        self.channel_type = channel_type
        self.is_active = is_active
        self.properties = properties

    def create(self):
        self.validate()
        return DeveloperChannel.from_db(db.create_dev_channel(self))

    def validate(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise Exception("Channel name must be a valid text value")
        if self.channel_type not in DeveloperChannel.SUPPORTED_CHANNEL_TYPES:
            raise Exception(f"Support channel types are {DeveloperChannel.SUPPORTED_CHANNEL_TYPES}")
        if not isinstance(self.properties, dict):
            raise Exception("Channel properties are required to create channel")
        if self.channel_type == "email":
            emails = self.properties.get("emails", [])
            if not isinstance(emails, list) or len(emails) == 0:
                raise Exception("Emails property must be list of emails")
            for index, email in enumerate(emails):
                if not validators.email(email or ''):
                    raise Exception(f"Email value at position {index + 1} is not valid")
        elif self.channel_type == "webhook":
            url = self.properties.get('url', '')
            if not validators.url(url or ''):
                raise Exception("Webhook property 'url' is required and cannot be empty")

    @classmethod
    def from_record(cls, rec) -> 'DeveloperChannel':
        return DeveloperChannel(rec.name, rec.channel_type, rec.properties, rec.rec.is_active, rec.id)

    @classmethod
    def from_db(cls, r: Union[Dict, Tuple]) -> 'DeveloperChannel':
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
            "is_active": self.is_active,
        }

    @staticmethod
    def find_all(sort_by, ascending, limit, offset):
        return [DeveloperChannel.from_db(channel) for channel in
                db.get_dev_channels(sort_by, ascending, limit, offset)]

    @staticmethod
    def find_by_id(channel_id):
        return DeveloperChannel.from_db(db.find_dev_channel_by_id(channel_id))

    @staticmethod
    def update_by_id(channel_id, name=None, properties=None, is_active=None, **kwargs):
        developer_channel = DeveloperChannel.find_by_id(channel_id)
        if not developer_channel:
            raise Exception("not found")
        if name:
            developer_channel.name = name
        if properties:
            developer_channel.properties = properties
        if isinstance(is_active, bool):
            developer_channel.is_active = is_active
        developer_channel.validate()
        return DeveloperChannel.from_db(db.update_dev_channel_by_id(channel_id, name, properties, is_active))

    @staticmethod
    def delete_by_id(channel_id):
        try:
            return DeveloperChannel.from_db(db.delete_dev_channel_by_id(channel_id))
        except Exception as e:
            if 'violates foreign key constraint' in str(e):
                raise Exception('cannot delete channel, channel has reference in channel-rule-map')
            raise e

    @classmethod
    def parse(cls, json: JSON) -> 'DeveloperChannel':
        if not isinstance(json.get('name'), str) or json.get('name').strip() == "":
            raise Exception("Channel name is required, it must be a string")
        if json.get('channel_type') not in DeveloperChannel.SUPPORTED_CHANNEL_TYPES:
            raise Exception(f"Channel type must be one of {DeveloperChannel.SUPPORTED_CHANNEL_TYPES}")
        if not isinstance(json.get('properties'), dict):
            raise Exception("Channel properties are required")
        return DeveloperChannel(**json)
