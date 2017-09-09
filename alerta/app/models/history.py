
from datetime import datetime

from alerta.app.utils.api import absolute_url


class History(object):

    def __init__(self, id, event, **kwargs):
        self.id = id
        self.event = event
        self.severity = kwargs.get('severity', None)
        self.status = kwargs.get('status', None)
        self.value = kwargs.get('value', None)
        self.change_type = kwargs.get('change_type', kwargs.get('type', None)) or ""
        self.text = kwargs.get('text', None)
        self.update_time = kwargs.get('update_time', None) or datetime.utcnow()

    @property
    def serialize(self):
        return {
            'id': self.id,
            'href': absolute_url('/alert/' + self.id),
            'event': self.event,
            'severity': self.severity,
            'status': self.status,
            'value': self.value,
            'type': self.change_type,
            'text': self.text,
            'updateTime': self.update_time
        }

    def __repr__(self):
        return 'History(id=%r, event=%r, severity=%r, status=%r, type=%r)' % (
            self.id, self.event, self.severity, self.status, self.change_type)

    @classmethod
    def from_document(cls, doc):
        return History(
            id=doc.get('id', None),
            event=doc.get('event'),
            severity=doc.get('severity', None),
            status=doc.get('status', None),
            value=doc.get('value', None),
            change_type=doc.get('type', None),
            text=doc.get('text', None),
            update_time=doc.get('updateTime', None)
        )

    @classmethod
    def from_record(cls, rec):
        return History(
            id=rec.id,
            event=rec.event,
            severity=rec.severity,
            status=rec.status,
            value=rec.value,
            change_type=rec.type,
            text=rec.text,
            update_time=rec.update_time
        )

    @classmethod
    def from_db(cls, r):
        if isinstance(r, dict):
            return cls.from_document(r)
        elif isinstance(r, tuple):
            return cls.from_record(r)
