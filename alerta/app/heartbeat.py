
import os
import sys
import platform
import time
import datetime
import pytz
import json

from uuid import uuid4
from email import utils


DEFAULT_TIMEOUT = 300  # seconds

prog = os.path.basename(sys.argv[0])


class Heartbeat(object):

    def __init__(self, origin=None, tags=None, create_time=None, timeout=None, customer=None):

        self.id = str(uuid4())
        self.origin = origin or '%s/%s' % (prog, platform.uname()[1])
        self.tags = tags or list()
        self.event_type = 'Heartbeat'
        self.create_time = create_time or datetime.datetime.utcnow()
        self.timeout = timeout or DEFAULT_TIMEOUT
        self.receive_time = None
        self.customer = customer

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
            'createTime': self.get_date('create_time', 'iso'),
            'timeout': self.timeout,
            'customer': self.customer
        }

    def get_date(self, attr, fmt='iso', timezone='Europe/London'):

        tz = pytz.timezone(timezone)

        if hasattr(self, attr):
            if fmt == 'local':
                return getattr(self, attr).replace(tzinfo=pytz.UTC).astimezone(tz).strftime('%Y/%m/%d %H:%M:%S')
            elif fmt == 'iso' or fmt == 'iso8601':
                return getattr(self, attr).replace(microsecond=0).isoformat() + ".%03dZ" % (getattr(self, attr).microsecond // 1000)
            elif fmt == 'rfc' or fmt == 'rfc2822':
                return utils.formatdate(time.mktime(getattr(self, attr).replace(tzinfo=pytz.UTC).timetuple()), True)
            elif fmt == 'short':
                return getattr(self, attr).replace(tzinfo=pytz.UTC).astimezone(tz).strftime('%a %d %H:%M:%S')
            elif fmt == 'epoch':
                return time.mktime(getattr(self, attr).replace(tzinfo=pytz.UTC).timetuple())
            elif fmt == 'raw':
                return getattr(self, attr)
            else:
                raise ValueError("Unknown date format %s" % fmt)
        else:
            return ValueError("Attribute %s not a date" % attr)

    def get_type(self):
        return self.event_type

    def receive_now(self):
        self.receive_time = datetime.datetime.utcnow()

    def __repr__(self):
        return 'Heartbeat(id=%r, origin=%r, create_time=%r, timeout=%r, customer=%r)' % (
            self.id, self.origin, self.create_time, self.timeout, self.customer)

    def __str__(self):
        return json.dumps(self.get_body())

    @staticmethod
    def parse_heartbeat(heartbeat):

        try:
            if isinstance(heartbeat, bytes):
                heartbeat = json.loads(heartbeat.decode('utf-8'))  # See https://bugs.python.org/issue10976
            else:
                heartbeat = json.loads(heartbeat)
        except ValueError as e:
            raise ValueError('Could not parse heartbeat - %s: %s' % (e, heartbeat))

        if heartbeat.get('createTime', None):
            try:
                heartbeat['createTime'] = datetime.datetime.strptime(heartbeat['createTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
            except ValueError as e:
                raise ValueError('Could not parse date time string: %s' % e)
        if heartbeat.get('tags', None):
            if not isinstance(heartbeat['tags'], list):
                raise ValueError('Attribute must be list: tags')

        return Heartbeat(
            origin=heartbeat.get('origin', None),
            tags=heartbeat.get('tags', list()),
            create_time=heartbeat.get('createTime', None),
            timeout=heartbeat.get('timeout', None),
            customer=heartbeat.get('customer', None)
        )


class HeartbeatDocument(object):

    def __init__(self, id, origin, tags, event_type, create_time, timeout, receive_time, customer):

        self.id = id
        self.origin = origin
        self.tags = tags
        self.event_type = event_type or 'Heartbeat'
        self.create_time = create_time or datetime.datetime.utcnow()
        self.timeout = timeout or DEFAULT_TIMEOUT
        self.receive_time = receive_time
        self.customer = customer

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
            'createTime': self.get_date('create_time', 'iso'),
            'timeout': self.timeout,
            'receiveTime': self.get_date('receive_time', 'iso'),
            'customer': self.customer
        }

    def get_date(self, attr, fmt='iso', timezone='Europe/London'):

        tz = pytz.timezone(timezone)

        if hasattr(self, attr):
            if fmt == 'local':
                return getattr(self, attr).replace(tzinfo=pytz.UTC).astimezone(tz).strftime('%Y/%m/%d %H:%M:%S')
            elif fmt == 'iso' or fmt == 'iso8601':
                return getattr(self, attr).replace(microsecond=0).isoformat() + ".%03dZ" % (getattr(self, attr).microsecond // 1000)
            elif fmt == 'rfc' or fmt == 'rfc2822':
                return utils.formatdate(time.mktime(getattr(self, attr).replace(tzinfo=pytz.UTC).timetuple()), True)
            elif fmt == 'short':
                return getattr(self, attr).replace(tzinfo=pytz.UTC).astimezone(tz).strftime('%a %d %H:%M:%S')
            elif fmt == 'epoch':
                return time.mktime(getattr(self, attr).replace(tzinfo=pytz.UTC).timetuple())
            elif fmt == 'raw':
                return getattr(self, attr)
            else:
                raise ValueError("Unknown date format %s" % fmt)
        else:
            return ValueError("Attribute %s not a date" % attr)

    def __repr__(self):
        return 'HeartbeatDocument(id=%r, origin=%r, create_time=%r, timeout=%r, customer=%r)' % (
            self.id, self.origin, self.create_time, self.timeout, self.customer)

    def __str__(self):
        return json.dumps(self.get_body())

    @staticmethod
    def parse_heartbeat(heartbeat):

        for k, v in heartbeat.items():
            if k in ['createTime', 'receiveTime']:
                if '.' in v:
                    try:
                        heartbeat[k] = datetime.datetime.strptime(v, '%Y-%m-%dT%H:%M:%S.%fZ')
                    except ValueError as e:
                        raise ValueError('Could not parse date time string: %s' % e)
                else:
                    try:
                        heartbeat[k] = datetime.datetime.strptime(v, '%Y-%m-%dT%H:%M:%SZ')  # if us = 000000
                    except ValueError as e:
                        raise ValueError('Could not parse date time string: %s' % e)

        return HeartbeatDocument(
            id=heartbeat.get('id', None),
            origin=heartbeat.get('origin', None),
            tags=heartbeat.get('tags', list()),
            event_type=heartbeat.get('type', None),
            create_time=heartbeat.get('createTime', None),
            timeout=heartbeat.get('timeout', None),
            receive_time=heartbeat.get('receiveTime', None),
            customer=heartbeat.get('customer', None)
        )
