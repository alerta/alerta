from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

from flask import g

from alerta.app import db
from alerta.database.base import Query
from alerta.models.enums import ChangeType, NoteType
from alerta.models.history import History
from alerta.utils.format import DateTime
from alerta.utils.response import absolute_url

JSON = Dict[str, Any]


class Note:

    def __init__(self, text: str, user: str, note_type: str, **kwargs) -> None:

        self.id = kwargs.get('id') or str(uuid4())
        self.text = text
        self.user = user
        self.note_type = note_type
        self.attributes = kwargs.get('attributes', None) or dict()
        self.create_time = kwargs['create_time'] if 'create_time' in kwargs else datetime.utcnow()
        self.update_time = kwargs.get('update_time')
        self.alert = kwargs.get('alert')
        self.customer = kwargs.get('customer')

    @classmethod
    def parse(cls, json: JSON) -> 'Note':
        return Note(
            id=json.get('id', None),
            text=json.get('status', None),
            user=json.get('status', None),
            attributes=json.get('attributes', dict()),
            note_type=json.get('type', None),
            create_time=DateTime.parse(json['createTime']) if 'createTime' in json else None,
            update_time=DateTime.parse(json['updateTime']) if 'updateTime' in json else None,
            alert=json.get('related', {}).get('alert'),
            customer=json.get('customer', None)
        )

    @property
    def serialize(self) -> Dict[str, Any]:
        note = {
            'id': self.id,
            'href': absolute_url('/note/' + self.id),
            'text': self.text,
            'user': self.user,
            'attributes': self.attributes,
            'type': self.note_type,
            'createTime': self.create_time,
            'updateTime': self.update_time,
            '_links': dict(),
            'customer': self.customer
        }  # type: Dict[str, Any]
        if self.alert:
            note['_links'] = {
                'alert': absolute_url('/alert/' + self.alert)
            }
        return note

    def __repr__(self) -> str:
        return 'Note(id={!r}, text={!r}, user={!r}, type={!r}, customer={!r})'.format(
            self.id, self.text, self.user, self.note_type, self.customer
        )

    @classmethod
    def from_document(cls, doc: Dict[str, Any]) -> 'Note':
        return Note(
            id=doc.get('id', None) or doc.get('_id'),
            text=doc.get('text', None),
            user=doc.get('user', None),
            attributes=doc.get('attributes', dict()),
            note_type=doc.get('type', None),
            create_time=doc.get('createTime'),
            update_time=doc.get('updateTime'),
            alert=doc.get('alert'),
            customer=doc.get('customer')
        )

    @classmethod
    def from_record(cls, rec) -> 'Note':
        return Note(
            id=rec.id,
            text=rec.text,
            user=rec.user,
            attributes=dict(rec.attributes),
            note_type=rec.type,
            create_time=rec.create_time,
            update_time=rec.update_time,
            alert=rec.alert,
            customer=rec.customer
        )

    @classmethod
    def from_db(cls, r: Union[Dict, Tuple]) -> 'Note':
        if isinstance(r, dict):
            return cls.from_document(r)
        elif isinstance(r, tuple):
            return cls.from_record(r)

    def create(self) -> 'Note':
        return Note.from_db(db.create_note(self))

    @staticmethod
    def from_alert(alert, text):
        note = Note(
            text=text,
            user=g.login,
            note_type=NoteType.alert,
            attributes=dict(
                resource=alert.resource,
                event=alert.event,
                environment=alert.environment,
                severity=alert.severity,
                status=alert.status
            ),
            alert=alert.id,
            customer=alert.customer
        )

        history = History(
            id=note.id,
            event=alert.event,
            severity=alert.severity,
            status=alert.status,
            value=alert.value,
            text=text,
            change_type=ChangeType.note,
            update_time=datetime.utcnow(),
            user=g.login
        )
        db.add_history(alert.id, history)
        return note.create()

    @staticmethod
    def find_by_id(id: str) -> Optional['Note']:
        return Note.from_db(db.get_note(id))

    @staticmethod
    def find_all(query: Query = None) -> List['Note']:
        return [Note.from_db(note) for note in db.get_notes(query)]

    def update(self, **kwargs) -> 'Note':
        return Note.from_db(db.update_note(self.id, **kwargs))

    def delete(self) -> bool:
        return db.delete_note(self.id)
