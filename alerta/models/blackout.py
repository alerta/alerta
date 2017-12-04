
from datetime import datetime, timedelta
from uuid import uuid4

from flask import current_app

from alerta.app import db
from alerta.utils.api import absolute_url
from alerta.utils.format import DateTime


class Blackout(object):

    def __init__(self, environment, **kwargs):
        if not environment:
            raise ValueError('Missing mandatory value for "environment"')

        start_time = kwargs.get('start_time', None) or datetime.utcnow()
        if kwargs.get('end_time', None):
            end_time = kwargs.get('end_time')
            duration = int((end_time - start_time).total_seconds())
        else:
            duration = kwargs.get('duration', None) or current_app.config['BLACKOUT_DURATION']
            end_time = start_time + timedelta(seconds=duration)

        self.id = kwargs.get('id', str(uuid4()))
        self.environment = environment
        self.service = kwargs.get('service', None) or list()
        self.resource = kwargs.get('resource', None)
        self.event = kwargs.get('event', None)
        self.group = kwargs.get('group', None)
        self.tags = kwargs.get('tags', None) or list()
        self.customer = kwargs.get('customer', None)
        self.start_time = start_time
        self.end_time = end_time
        self.duration = duration

        if self.environment:
            self.priority = 1
        if self.resource and not self.event:
            self.priority = 2
        elif self.service:
            self.priority = 3
        elif self.event and not self.resource:
            self.priority = 4
        elif self.group:
            self.priority = 5
        elif self.resource and self.event:
            self.priority = 6
        elif self.tags:
            self.priority = 7

        now = datetime.utcnow()
        if self.start_time <= now and self.end_time > now:
            self.status = "active"
            self.remaining = int((self.end_time - now).total_seconds())
        elif self.start_time > now:
            self.status = "pending"
            self.remaining = self.duration
        elif self.end_time <= now:
            self.status = "expired"
            self.remaining = 0

    @classmethod
    def parse(cls, json):
        if not isinstance(json.get('service', []), list):
            raise ValueError('service must be a list')
        if not isinstance(json.get('tags', []), list):
            raise ValueError('tags must be a list')

        return Blackout(
            environment=json.get('environment'),
            service=json.get('service', list()),
            resource=json.get('resource', None),
            event=json.get('event', None),
            group=json.get('group', None),
            tags=json.get('tags', list()),
            customer=json.get('customer', None),
            start_time=DateTime.parse(json.get('startTime')),
            end_time=DateTime.parse(json.get('endTime')),
            duration=json.get('duration', None)
        )

    @property
    def serialize(self):
        return {
            'id': self.id,
            'href': absolute_url('/blackout/' + self.id),
            'priority': self.priority,
            'environment': self.environment,
            'service': self.service,
            'resource': self.resource,
            'event': self.event,
            'group': self.group,
            'tags': self.tags,
            'customer': self.customer,
            'startTime': self.start_time,
            'endTime': self.end_time,
            'duration': self.duration,
            'status': self.status,
            'remaining': self.remaining
        }

    def __repr__(self):
        more = ''
        if self.service:
            more += 'service=%r, ' % self.service
        if self.resource:
            more += 'resource=%r, ' % self.resource
        if self.event:
            more += 'event=%r, ' % self.event
        if self.group:
            more += 'group=%r, ' % self.group
        if self.tags:
            more += 'tags=%r, ' % self.tags
        if self.customer:
            more += 'customer=%r, ' % self.customer

        return 'Blackout(id=%r, priority=%r, status=%r, environment=%r, %sstart_time=%r, end_time=%r, remaining=%r)' % (
            self.id,
            self.priority,
            self.status,
            self.environment,
            more,
            self.start_time,
            self.end_time,
            self.remaining
        )

    @classmethod
    def from_document(cls, doc):
        return Blackout(
            id=doc.get('id', None) or doc.get('_id'),
            priority=doc.get('priority', None),
            environment=doc.get('environment'),
            service=doc.get('service', list()),
            resource=doc.get('resource', None),
            event=doc.get('event', None),
            group=doc.get('group', None),
            tags=doc.get('tags', list()),
            customer=doc.get('customer', None),
            start_time=doc.get('startTime', None),
            end_time=doc.get('endTime', None),
            duration=doc.get('duration', None)
        )

    @classmethod
    def from_record(cls, rec):
        return Blackout(
            id=rec.id,
            priority=rec.priority,
            environment=rec.environment,
            service=rec.service,
            resource=rec.resource,
            event=rec.event,
            group=rec.group,
            tags=rec.tags,
            customer=rec.customer,
            start_time=rec.start_time,
            end_time=rec.end_time,
            duration=rec.duration
        )

    @classmethod
    def from_db(cls, r):
        if isinstance(r, dict):
            return cls.from_document(r)
        elif isinstance(r, tuple):
            return cls.from_record(r)
        else:
            return

    # create a blackout
    def create(self):
        return Blackout.from_db(db.create_blackout(self))

    # get a blackout
    @staticmethod
    def find_by_id(id, customer=None):
        return Blackout.from_db(db.get_blackout(id, customer))

    @staticmethod
    def find_all(query=None):
        return [Blackout.from_db(blackout) for blackout in db.get_blackouts(query)]

    def delete(self):
        return db.delete_blackout(self.id)
