import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

from cryptography.fernet import Fernet
from flask import current_app
from python_http_client.exceptions import ForbiddenError, UnauthorizedError
from sendgrid import SendGridAPIClient, SendGridException
from sendgrid.helpers.mail import Mail
from twilio.base.exceptions import TwilioException, TwilioRestException
from twilio.rest import Client as TwilioClient

from alerta.app import db
from alerta.database.base import Query
from alerta.exceptions import ApiError
from alerta.utils.response import absolute_url

LOG = logging.getLogger('alerta.models.notification_channel')

JSON = Dict[str, Any]


class NotificationChannel:

    def __init__(self, _type: str, api_token: str, sender: str, **kwargs) -> None:
        self.id = kwargs.get('id') or str(uuid4())
        self.type = _type
        self.api_token = api_token  # encrypted
        self.sender = sender
        self.host = kwargs.get('host', None)
        self.platform_id = kwargs.get('platform_id', None)
        self.platform_partner_id = kwargs.get('platform_partner_id', None)
        self.api_sid: 'str|None' = kwargs.get('api_sid', None)  # encrypted
        self.customer = kwargs.get('customer', None)
        self.verify = kwargs.get('verify', None)

    @classmethod
    def parse(cls, json: JSON) -> 'NotificationChannel':
        fernet = Fernet(current_app.config['NOTIFICATION_KEY'])
        return NotificationChannel(
            id=json.get('id', None),
            _type=json['type'],
            api_token=fernet.encrypt(str(json['apiToken']).encode()).decode(),
            api_sid=fernet.encrypt(str(json['apiSid']).encode()).decode() if 'apiSid' in json else None,
            sender=json['sender'],
            host=json.get('host', None),
            platform_id=json.get('platfromId', None),
            platform_partner_id=json.get('platfromPartnerId', None),
            customer=json.get('customer', None),
            verify=json.get('verify', None),
        )

    @ property
    def serialize(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'href': absolute_url('/notificationchannel/' + self.id),
            'type': self.type,
            'sender': self.sender,
            'customer': self.customer,
            'host': self.host,
            'platformId': self.platform_id,
            'platformPartnerId': self.platform_partner_id,
            'verify': self.verify
        }

    def __repr__(self) -> str:
        more = ''
        if self.customer:
            more += f'customer={self.customer}, '
        return f'NotificationChannel(id={self.id}, type={self.type}, sender={self.sender}, {more}'

    @ classmethod
    def from_document(cls, doc: Dict[str, Any]) -> 'NotificationChannel':
        return NotificationChannel(
            id=doc.get('id', None) or doc.get('_id'),
            _type=doc['type'],
            api_token=doc['apiToken'],
            api_sid=doc.get('apiSid', None),
            sender=doc['sender'],
            host=doc.get('host', None),
            platform_id=doc.get('platfromId', None),
            platform_partner_id=doc.get('platfromPartnerId', None),
            customer=doc.get('customer', None),
            verify=doc.get('verify', None),
        )

    @ classmethod
    def from_record(cls, rec) -> 'NotificationChannel':
        return NotificationChannel(
            id=rec.id,
            _type=rec.type,
            api_token=rec.api_token,
            api_sid=rec.api_sid,
            sender=rec.sender,
            host=rec.host,
            platform_id=rec.platform_id,
            platform_partner_id=rec.platform_partner_id,
            customer=rec.customer,
            verify=rec.verify,
        )

    @ classmethod
    def from_db(cls, r: Union[Dict, Tuple]) -> 'NotificationChannel':
        if isinstance(r, dict):
            return cls.from_document(r)
        elif isinstance(r, tuple):
            return cls.from_record(r)

    # create a notification rule
    def create(self) -> 'NotificationChannel':
        return NotificationChannel.from_db(db.create_notification_channel(self))

    # get a notification rule
    @ staticmethod
    def find_by_id(id: str, customers: 'list[str]|None' = None) -> Optional['NotificationChannel']:
        return NotificationChannel.from_db(db.get_notification_channel(id, customers))

    @ staticmethod
    def find_all(query: 'Query|None' = None, page: int = 1, page_size: int = 1000) -> List['NotificationChannel']:
        return [
            NotificationChannel.from_db(notification_channel)
            for notification_channel in db.get_notification_channels(query, page, page_size)
        ]

    @ staticmethod
    def count(query: 'Query|None' = None) -> int:
        return db.get_notification_channels_count(query)

    def update(self, **kwargs) -> 'NotificationChannel':
        return NotificationChannel.from_db(db.update_notification_channel(self.id, **kwargs))

    def delete(self) -> bool:
        return db.delete_notification_channel(self.id)
