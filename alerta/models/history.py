
from datetime import datetime

from alerta.utils.response import absolute_url


class History:

    def __init__(self, id, event, **kwargs):
        self.id = id
        self.event = event
        self.severity = kwargs.get('severity', None)
        self.status = kwargs.get('status', None)
        self.value = kwargs.get('value', None)
        self.text = kwargs.get('text', None)
        self.change_type = kwargs.get('change_type', kwargs.get('type', None)) or ''
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
            'text': self.text,
            'type': self.change_type,
            'updateTime': self.update_time
        }

    def __repr__(self):
        return 'History(id={!r}, event={!r}, severity={!r}, status={!r}, type={!r})'.format(
            self.id, self.event, self.severity, self.status, self.change_type)

    @classmethod
    def from_document(cls, doc):
        return History(
            id=doc.get('id', None),
            event=doc.get('event'),
            severity=doc.get('severity', None),
            status=doc.get('status', None),
            value=doc.get('value', None),
            text=doc.get('text', None),
            change_type=doc.get('type', None),
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
            text=rec.text,
            change_type=rec.type,
            update_time=rec.update_time
        )

    @classmethod
    def from_db(cls, r):
        if isinstance(r, dict):
            return cls.from_document(r)
        elif isinstance(r, tuple):
            return cls.from_record(r)


class RichHistory:

    def __init__(self, resource, event, **kwargs):

        self.id = kwargs.get('id', None)
        self.resource = resource
        self.event = event
        self.environment = kwargs.get('environment', None)
        self.severity = kwargs.get('severity', None)
        self.status = kwargs.get('status', None)
        self.service = kwargs.get('service', None) or list()
        self.group = kwargs.get('group', None)
        self.value = kwargs.get('value', None)
        self.text = kwargs.get('text', None)
        self.tags = kwargs.get('tags', None) or list()
        self.attributes = kwargs.get('attributes', None) or dict()
        self.origin = kwargs.get('origin', None)
        self.update_time = kwargs.get('update_time', None)
        self.change_type = kwargs.get('change_type', kwargs.get('type', None))
        self.customer = kwargs.get('customer', None)

    @property
    def serialize(self):
        data = {
            'id': self.id,
            'href': absolute_url('/alert/' + self.id),
            'resource': self.resource,
            'event': self.event,
            'environment': self.environment,
            'service': self.service,
            'group': self.group,
            'text': self.text,
            'tags': self.tags,
            'attributes': self.attributes,
            'origin': self.origin,
            'updateTime': self.update_time,
            'type': self.change_type,
            'customer': self.customer
        }

        if self.severity:
            data['severity'] = self.severity

        if self.status:
            data['status'] = self.status

        if self.value:
            data['value'] = self.value

        return data

    def __repr__(self):
        return 'RichHistory(id={!r}, environment={!r}, resource={!r}, event={!r}, severity={!r}, status={!r}, type={!r}, customer={!r})'.format(
            self.id, self.environment, self.resource, self.event, self.severity, self.status, self.change_type, self.customer)

    @classmethod
    def from_document(cls, doc):
        return RichHistory(
            id=doc.get('id', None) or doc.get('_id'),
            resource=doc.get('resource', None),
            event=doc.get('event', None),
            environment=doc.get('environment', None),
            severity=doc.get('severity', None),
            status=doc.get('status', None),
            service=doc.get('service', list()),
            group=doc.get('group', None),
            value=doc.get('value', None),
            text=doc.get('text', None),
            tags=doc.get('tags', list()),
            attributes=doc.get('attributes', dict()),
            origin=doc.get('origin', None),
            update_time=doc.get('updateTime', None),
            change_type=doc.get('type', None),
            customer=doc.get('customer', None)
        )

    @classmethod
    def from_record(cls, rec):
        return RichHistory(
            id=rec.id,
            resource=rec.resource,
            event=rec.event,
            environment=rec.environment,
            severity=rec.severity,
            status=rec.status,
            service=rec.service,
            group=rec.group,
            value=rec.value,
            text=rec.text,
            tags=rec.tags,
            attributes=dict(rec.attributes),
            origin=rec.origin,
            update_time=rec.update_time,
            change_type=rec.type,
            customer=rec.customer
        )

    @classmethod
    def from_db(cls, r):
        if isinstance(r, dict):
            return cls.from_document(r)
        elif isinstance(r, tuple):
            return cls.from_record(r)
