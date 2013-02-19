
import os
import datetime
import json

from uuid import uuid4

from alerta.alert import severity
from alerta.log import logging

_DEFAULT_TIMEOUT = 3600  # default number of seconds before alert is EXPIRED


class Alert(object):

    def __init__(self, resource, event, correlate=list(), group='Misc', value=None,
                 severity=severity.NORMAL, environment=list('PROD'), service=list(),
                 text=None, event_type='exceptionAlert', tags=list(), origin=None,
                 threshold_info=None, summary=None, timeout=_DEFAULT_TIMEOUT):

        # FIXME(nsatterl): how to fix __program__ for origin???
        __program__ = 'THIS IS BROKEN'

        self.alertid = str(uuid4())
        self.origin = origin or '%s/%s' % (__program__, os.uname()[1])
        self.summary = summary or '%s - %s %s is %s on %s %s' % (','.join(environment), severity, event,
                                                     value, ','.join(service), resource)
        self.header = {
            'type': event_type,
            'correlation-id': self.alertid,
        }

        self.alert = {
            'id': self.alertid,
            'resource': resource,
            'event': event,
            'correlatedEvents': correlate,
            'group': group,
            'value': value,
            'severity': severity,
            'environment': environment,
            'service': service,
            'text': text,
            'type': event_type,
            'tags': tags,
            'summary': summary,
            'createTime': datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + 'Z',
            'origin': origin,
            'thresholdInfo': threshold_info,
            'timeout': timeout,
        }

    def __repr__(self):
        return self.header, self.alert

    def __str__(self):
        return json.dumps(self.alert, indent=4)

    def get_alertid(self):
        return self.alertid

    def send_alert(self):

        LOG.debug("%s : Sending ... %s" % (self.alert['id'], self.alert))
        pass


class Heartbeat(object):

    def __init__(self, ):


    def send_heartbeat(self):

        # self.header
        pass

