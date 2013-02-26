
import os
import datetime
import json

from uuid import uuid4

from alerta.alert import severity, status
from alerta.common import log as logging
from alerta.common.utils import DateEncoder

_DEFAULT_TIMEOUT = 3600  # default number of seconds before alert is EXPIRED

LOG = logging.getLogger(__name__)


class Alert(object):

    def __init__(self, resource, event, correlate=list(), group='Misc', value=None, status=status.UNKNOWN,
                 severity=severity.NORMAL, previous_severity=None, environment=['PROD'], service=list(),
                 text=None, event_type='exceptionAlert', tags=list(), origin=None, repeat=False, duplicate_count=0,
                 threshold_info='n/a', summary=None, timeout=_DEFAULT_TIMEOUT, alertid=None, last_receive_id=None,
                 create_time=None, receive_time=None, last_receive_time=None, trend_indication=None):

        # FIXME(nsatterl): how to fix __program__ for origin???
        __program__ = 'THIS IS BROKEN'

        self.alertid = alertid or str(uuid4())
        self.summary = summary or '%s - %s %s is %s on %s %s' % (','.join(environment), severity, event, value, ','.join(service), resource)

        self.header = {
            'type': event_type,
            'correlation-id': self.alertid,
        }

        create_time = create_time or datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + 'Z'

        self.alert = {
            'id': self.alertid,
            'resource': resource,
            'event': event,
            'correlatedEvents': correlate,
            'group': group,
            'value': value,
            'severity': severity,
            'previousSeverity': previous_severity or 'UNKNOWN',   # severity.UNKNOWN,
            'environment': environment,
            'service': service,
            'text': text,
            'type': event_type,
            'tags': tags,
            'summary': self.summary,
            'createTime': create_time,
            'origin': origin or '%s/%s' % (__program__, os.uname()[1]),
            'thresholdInfo': threshold_info,
            'timeout': timeout,
            'expireTime': 'calculate the expire time from createTime+timeout',  # TODO(nsatterl); fix this
            'repeat': repeat,
            'duplicateCount': duplicate_count,
        }

        if status:
            self.alert['status'] = status
        if receive_time:
            self.alert['receiveTime'] = receive_time
        if last_receive_time:
            self.alert['lastReceiveTime'] = last_receive_time
        if last_receive_id:
            self.alert['lastReceiveId'] = last_receive_id
        if trend_indication:
            self.alert['trendIndication'] = trend_indication

    def __repr__(self):
        return 'Alert(header=%r, alert=%r)' % (str(self.header), str(self.alert))

    def __str__(self):
        return json.dumps(self.alert, indent=4)

    def get_id(self):
        return self.alertid

    def get_header(self):
        return self.header

    def get_body(self):
        return self.alert


class Heartbeat(object):

    def __init__(self, origin=None, version='unknown'):

        # FIXME(nsatterl): how to fix __program__ for origin???
        __program__ = 'THIS IS BROKEN'

        self.heartbeatid = str(uuid4())
        self.origin = origin or '%s/%s' % (__program__, os.uname()[1])

        self.header = {
            'type': 'heartbeat',
            'correlation-id': self.heartbeatid,
        }

        self.heartbeat = {
            'id': self.heartbeatid,
            'type': 'heartbeat',
            'createTime': datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + 'Z',
            'origin': origin,
            'version': version,
        }

    def __repr__(self):
        return self.header, self.heartbeat

    def __str__(self):
        return json.dumps(self.heartbeat, indent=4)

    def get_id(self):
        return self.heartbeatid

    def get_header(self):
        return self.header

    def get_body(self):
        return self.heartbeat

