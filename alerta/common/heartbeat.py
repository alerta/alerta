
import os
import sys
import datetime
import json
from uuid import uuid4

from alerta.common import log as logging
from alerta.common import config
from alerta.common.utils import DateEncoder

LOG = logging.getLogger(__name__)
CONF = config.CONF


class Heartbeat(object):

    def __init__(self, origin=None, version='unknown', heartbeatid=None, create_time=None):

        prog = os.path.basename(sys.argv[0])

        self.heartbeatid = heartbeatid or str(uuid4())
        self.event_type = 'Heartbeat'
        self.create_time = create_time or datetime.datetime.utcnow()
        self.origin = origin or '%s/%s' % (prog, os.uname()[1])
        self.version = version

    def get_id(self):
        return self.heartbeatid

    def get_header(self):

        header = {
            'type': self.event_type,
            'correlation-id': self.heartbeatid,
        }
        return header

    def get_body(self):

        heartbeat = {
            'id': self.heartbeatid,
            'type': self.event_type,
            'createTime': self.create_time,
            'origin': self.origin,
            'version': self.version,
        }
        return heartbeat

    def get_type(self):
        return self.event_type

    def receive_now(self):
        self.receive_time = datetime.datetime.utcnow()

    def __repr__(self):
        return 'Heartbeat(header=%r, heartbeat=%r)' % (self.get_header(), self.get_body())

    def __str__(self):
        return json.dumps(self.get_body(), cls=DateEncoder, indent=4)

    @staticmethod
    def parse_heartbeat(heartbeat):

        try:
            heartbeat = json.loads(heartbeat)
        except ValueError, e:
            LOG.error('Could not parse heartbeat: %s', e)
            return

        if heartbeat.get('createTime', None):
            try:
                heartbeat['createTime'] = datetime.datetime.strptime(heartbeat['createTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
            except ValueError, e:
                LOG.error('Could not parse date time string: %s', e)
                return

        return Heartbeat(
            origin=heartbeat.get('origin', None),
            version=heartbeat.get('version', None),
            heartbeatid=heartbeat.get('id', None),
            create_time=heartbeat.get('createTime', None),
        )
