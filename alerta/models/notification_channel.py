import json
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4
from alerta.exceptions import ApiError
from sendgrid import SendGridAPIClient, SendGridException
from python_http_client.exceptions import ForbiddenError, UnauthorizedError
from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioException, TwilioRestException

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
        self.api_token = api_token
        self.sender = sender
        self.host = kwargs.get('host', None)
        self.api_sid = kwargs.get('api_sid', None)
        self.customer = kwargs.get('customer', None)

    def validate(self):
        notification_type = self.type
        sender = self.sender
        if notification_type == 'sendgrid':
            try:
                response = SendGridAPIClient(self.api_token).send(
                    Mail(
                        from_email=sender,
                        to_emails=[sender],
                        subject="Alerta: Sendgrid Setup",
                        html_content='Hello,\n This is an automated message sent from alerta to ensure notification channel has been created corectly',
                    )
                )
                if response.status_code == 202:
                    return
            except (ForbiddenError, UnauthorizedError) as err:
                raise ApiError(f'validation of new notification channel "{self.id}" failed: sendgrid exception {str(err)}')
        elif 'twilio' in notification_type:
            try:
                client = TwilioClient(self.api_sid, self.api_token)
                client_numbers = [number.phone_number for number in client.incoming_phone_numbers.list()]
                account_numbers = [callid.phone_number for callid in client.outgoing_caller_ids.list()]
                if sender in client_numbers:
                    return
                if 'sms' in notification_type:

                    sms = client.messages.create(
                        body='Test Melding',
                        from_=sender,
                        #  to='+14155240970'
                        to=account_numbers[0],
                    )
            except (TwilioException, TwilioRestException) as err:
                raise ApiError(f'validation of new notification channel "{self.id}" failed: twilio exception {str(err)}')
        else:
            raise ApiError(
                f'validation of new notification channel "{self.id}" failed: type "{notification_type}" is not a known type. Please make sure that type is either sendgrid, twiliocall or twiliosms'
            )

    @classmethod
    def parse(cls, json: JSON) -> 'NotificationChannel':
        return NotificationChannel(
            id=json.get('id', None),
            _type=json['type'],
            api_token=json['apiToken'],
            api_sid=json.get('apiSid', None),
            sender=json['sender'],
            host=json.get('host', None),
            customer=json.get('customer', None),
        )

    @property
    def serialize(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'href': absolute_url('/notificationchannel/' + self.id),
            'type': self.type,
            'sender': self.sender,
            'customer': self.customer,
        }

    def __repr__(self) -> str:
        more = '' if not self.api_sid else f'api_sid={self.api_sid}, '
        if self.customer:
            more += f'customer={self.customer}, '
        return f'NotificationRule(id={self.id}, type={self.type}, api_token={self.api_token}, sender={self.sender}, {more}'

    @classmethod
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

    @classmethod
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

    @classmethod
    def from_db(cls, r: Union[Dict, Tuple]) -> 'NotificationChannel':
        if isinstance(r, dict):
            return cls.from_document(r)
        elif isinstance(r, tuple):
            return cls.from_record(r)

    # create a notification rule
    def create(self) -> 'NotificationChannel':
        # self.validate()
        # self.validate()
        return NotificationChannel.from_db(db.create_notification_channel(self))

    # get a notification rule
    @staticmethod
    def find_by_id(id: str, customers: List[str] = None) -> Optional['NotificationChannel']:
        return NotificationChannel.from_db(db.get_notification_channel(id, customers))

    @staticmethod
    def find_all(query: Query = None, page: int = 1, page_size: int = 1000) -> List['NotificationChannel']:
        return [
            NotificationChannel.from_db(notification_channel)
            for notification_channel in db.get_notification_channels(query, page, page_size)
        ]

    @staticmethod
    def count(query: Query = None) -> int:
        return db.get_notification_channels_count(query)

    def update(self, **kwargs) -> 'NotificationChannel':
        self.validate()
        return NotificationChannel.from_db(db.update_notification_channel(self.id, **kwargs))

    def delete(self) -> bool:
        return db.delete_notification_channel(self.id)
