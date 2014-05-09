
import os
import sys
import json
import datetime
import logging

from uuid import uuid4

prog = os.path.basename(sys.argv[0])

LOG = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 300  # seconds


class Heartbeat(object):

    def __init__(self, origin=None, tags=[], create_time=None, timeout=None):

        self.id = str(uuid4())
        self.origin = origin or '%s/%s' % (prog, os.uname()[1])
        self.tags = tags or list()
        self.event_type = 'Heartbeat'
        self.create_time = create_time or datetime.datetime.utcnow()
        self.timeout = timeout or DEFAULT_TIMEOUT
        self.receive_time = None

    def get_id(self, short=False):

        if short:
            return self.id[:8]
        else:
            return self.id

    def get_header(self):

        return {
            "origin": self.origin,
            "type": self.event_type,
            "correlation-id": self.id
        }

    def get_body(self):

        return {
            'id': self.id,
            'origin': self.origin,
            'tags': self.tags,
            'type': self.event_type,
            'createTime': self.create_time.replace(microsecond=0).isoformat() + ".%03dZ" % (self.create_time.microsecond // 1000),
            'timeout': self.timeout,
        }

    def get_type(self):
        return self.event_type

    def receive_now(self):
        self.receive_time = datetime.datetime.utcnow()

    def __repr__(self):
        return 'Heartbeat(id=%r, origin=%r, create_time=%r, timeout=%r)' % (self.id, self.origin, self.create_time, self.timeout)

    def __str__(self):
        return json.dumps(self.get_body(), indent=4)

    @staticmethod
    def parse_heartbeat(heartbeat):

        try:
            heartbeat = json.loads(heartbeat)
        except ValueError, e:
            raise ValueError('Could not parse heartbeat - %s: %s' % (e, heartbeat))

        if heartbeat.get('createTime', None):
            try:
                heartbeat['createTime'] = datetime.datetime.strptime(heartbeat['createTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
            except ValueError, e:
                raise ValueError('Could not parse date time string: %s' % e)

        return Heartbeat(
            origin=heartbeat.get('origin', None),
            tags=heartbeat.get('tags', None),
            create_time=heartbeat.get('createTime', None),
            timeout=heartbeat.get('timeout', None),
        )


class HeartbeatDocument(object):

    def __init__(self, id, origin, tags, event_type, create_time, timeout, receive_time):

        self.id = id
        self.origin = origin
        self.tags = tags
        self.event_type = event_type or 'Heartbeat'
        self.create_time = create_time or datetime.datetime.utcnow()
        self.timeout = timeout or DEFAULT_TIMEOUT
        self.receive_time = receive_time

    def get_id(self, short=False):

        if short:
            return self.id[:8]
        else:
            return self.id

    def get_header(self):

        return {
            "origin": self.origin,
            "type": self.event_type,
            "correlation-id": self.id
        }

    def get_body(self):

        return {
            'id': self.id,
            'origin': self.origin,
            'tags': self.tags,
            'type': self.event_type,
            'createTime': self.create_time.replace(microsecond=0).isoformat() + ".%03dZ" % (self.create_time.microsecond // 1000),
            'timeout': self.timeout,
            'receiveTime': self.receive_time.replace(microsecond=0).isoformat() + ".%03dZ" % (self.receive_time.microsecond // 1000)
        }

    def __repr__(self):
        return 'HeartbeatDocument(id=%r, origin=%r, create_time=%r, timeout=%r)' % (self.id, self.origin, self.create_time, self.timeout)

    def __str__(self):
        return json.dumps(self.get_body(), indent=4)

