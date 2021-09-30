import json
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4
from alerta.exceptions import ApiError
from sendgrid import SendGridAPIClient, SendGridException
from python_http_client.exceptions import ForbiddenError, UnauthorizedError
from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioException, TwilioRestException
from cryptography.fernet import Fernet
from flask import current_app

from alerta.app import db
from alerta.database.base import Query
from alerta.utils.response import absolute_url
from sendgrid.helpers.mail import Mail
import logging

LOG = logging.getLogger('alerta.models.notification_channel')

JSON = Dict[str, Any]


class NotificationChannel:

    def __init__(self, _type: str, api_token: str, sender: str, **kwargs) -> None:
        self.id = kwargs.get('id') or str(uuid4())
        self.type = _type
        self.api_token = api_token  # encrypted
        self.sender = sender
        self.host = kwargs.get('host', None)
        self.api_sid = kwargs.get('api_sid', None)  # encrypted
        self.customer = kwargs.get('customer', None)

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
            customer=json.get('customer', None),
        )

    @ property
    def serialize(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'href': absolute_url('/notificationchannel/' + self.id),
            'type': self.type,
            'sender': self.sender,
            'customer': self.customer,
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
            customer=doc.get('customer', None),
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
            customer=rec.customer,
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
    def find_by_id(id: str, customers: List[str] = None) -> Optional['NotificationChannel']:
        return NotificationChannel.from_db(db.get_notification_channel(id, customers))

    @ staticmethod
    def find_all(query: Query = None, page: int = 1, page_size: int = 1000) -> List['NotificationChannel']:
        return [
            NotificationChannel.from_db(notification_channel)
            for notification_channel in db.get_notification_channels(query, page, page_size)
        ]

    @ staticmethod
    def count(query: Query = None) -> int:
        return db.get_notification_channels_count(query)

    def update(self, **kwargs) -> 'NotificationChannel':
        return NotificationChannel.from_db(db.update_notification_channel(self.id, **kwargs))

    def delete(self) -> bool:
        return db.delete_notification_channel(self.id)
