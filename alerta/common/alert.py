import os
import sys
import datetime
import json
from uuid import uuid4
import re
import fnmatch

import yaml

from alerta.common import log as logging
from alerta.common import config
from alerta.common import status_code, severity_code
from alerta.common.utils import DateEncoder, isfloat


LOG = logging.getLogger(__name__)
CONF = config.CONF

ATTRIBUTES = [
    'resource',
    'event',
    'correlatedEvents',
    'group',
    'value',
    'status',
    'severity',
    'previousSeverity',
    'environment',
    'service',
    'text',
    'type',
    'tags',
    'origin',
    'repeat',
    'duplicateCount',
    'thresholdInfo',
    'summary',
    'timeout',
    'id',
    'lastReceiveId',
    'createTime',
    'expireTime',
    'receiveTime',
    'lastReceiveTime',
    'trendIndication',
    'rawData',
    'moreInfo',
    'graphUrls',
    'history',
]


class Alert(object):

    def __init__(self, resource, event, correlate=None, group='Misc', value=None, status=status_code.UNKNOWN,
                 severity=severity_code.NORMAL, previous_severity=severity_code.UNKNOWN, environment=None, service=None,
                 text=None, event_type='exceptionAlert', tags=None, origin=None, repeat=False, duplicate_count=0,
                 threshold_info='n/a', summary=None, timeout=None, alertid=None, last_receive_id=None,
                 create_time=None, expire_time=None, receive_time=None, last_receive_time=None, trend_indication=None,
                 raw_data=None, more_info=None, graph_urls=None, history=None):

        prog = os.path.basename(sys.argv[0])

        if not resource:
            raise ValueError('Missing mandatory value for resource')
        if not event:
            raise ValueError('Missing mandatory value for event')

        self.resource = resource
        self.event = event
        self.correlate = correlate or list()
        self.group = group

        if isfloat(value):
            self.value = '%.2f' % float(value)
        else:
            self.value = value or 'n/a'
        if status:
            self.status = status
        self.severity = severity
        self.previous_severity = previous_severity
        self.environment = environment or ['PROD']
        self.service = service or ['Undefined']
        self.text = text or ''
        self.event_type = event_type
        self.tags = tags or list()
        self.origin = origin or '%s/%s' % (prog, os.uname()[1])
        self.repeat = repeat
        self.duplicate_count = duplicate_count
        self.threshold_info = threshold_info
        self.summary = summary or '%s - %s %s is %s on %s %s' % (
            ','.join(self.environment), self.severity.capitalize(), self.event, self.value, ','.join(self.service), self.resource)
        self.timeout = timeout or CONF.timeout
        self.alertid = alertid or str(uuid4())
        if last_receive_id:
            self.last_receive_id = last_receive_id
        self.create_time = create_time or datetime.datetime.utcnow()
        self.expire_time = expire_time or self.create_time + datetime.timedelta(seconds=self.timeout)
        if receive_time:
            self.receive_time = receive_time
        if last_receive_time:
            self.last_receive_time = last_receive_time
        if trend_indication:
            self.trend_indication = trend_indication
        self.raw_data = raw_data
        self.more_info = more_info
        self.graph_urls = graph_urls or list()
        if history:
            self.history = history

    def get_id(self, short=False):
        if short:
            return self.alertid.split('-')[0]
        else:
            return self.alertid

    def get_header(self):

        header = {
            'type': self.event_type,
            'correlation-id': self.alertid,
        }
        return header

    def get_body(self):

        alert = {
            'resource': self.resource,
            'event': self.event,
            'correlatedEvents': self.correlate,
            'group': self.group,
            'value': self.value,
            'severity': self.severity,
            'previousSeverity': self.previous_severity,
            'environment': self.environment,
            'service': self.service,
            'text': self.text,
            'type': self.event_type,
            'tags': self.tags,
            'origin': self.origin,
            'repeat': self.repeat,
            'duplicateCount': self.duplicate_count,
            'thresholdInfo': self.threshold_info,
            'summary': self.summary,
            'timeout': self.timeout,
            'id': self.alertid,
            'createTime': self.create_time,
            'expireTime': self.expire_time,
            'rawData': self.raw_data,
            'moreInfo': self.more_info,
            'graphUrls': self.graph_urls,
        }

        if hasattr(self, 'status'):
            alert['status'] = self.status
        if hasattr(self, 'receive_time'):
            alert['receiveTime'] = self.receive_time
        if hasattr(self, 'last_receive_time'):
            alert['lastReceiveTime'] = self.last_receive_time
        if hasattr(self, 'last_receive_id'):
            alert['lastReceiveId'] = self.last_receive_id
        if hasattr(self, 'trend_indication'):
            alert['trendIndication'] = self.trend_indication
        if hasattr(self, 'history'):
            alert['history'] = self.history

        return alert

    def get_type(self):
        return self.event_type

    def get_severity(self):
        return self.severity

    def get_create_time(self):
        return self.create_time.replace(microsecond=0).isoformat() + ".%03dZ" % (self.create_time.microsecond // 1000)

    def get_receive_time(self):
        return self.receive_time.replace(microsecond=0).isoformat() + ".%03dZ" % (self.receive_time.microsecond // 1000)

    def get_last_receive_time(self):
        return self.last_receive_time.replace(microsecond=0).isoformat() + ".%03dZ" % (self.last_receive_time.microsecond // 1000)

    def receive_now(self):
        self.receive_time = datetime.datetime.utcnow()

    def __repr__(self):
        return 'Alert(header=%r, alert=%r)' % (self.get_header(), self.get_body())

    def __str__(self):
        return json.dumps(self.get_body(), cls=DateEncoder, indent=4)

    @staticmethod
    def parse_alert(alert):

        try:
            alert = json.loads(alert)
        except ValueError, e:
            LOG.error('Could not parse alert: %s', e)
            return

        for k, v in alert.iteritems():
            if k in ['createTime', 'receiveTime', 'lastReceiveTime', 'expireTime']:
                try:
                    alert[k] = datetime.datetime.strptime(v, '%Y-%m-%dT%H:%M:%S.%fZ')
                except ValueError, e:
                    LOG.error('Could not parse date time string: %s', e)
                    return

        return Alert(
            resource=alert.get('resource', None),
            event=alert.get('event', None),
            correlate=alert.get('correlatedEvents', None),
            group=alert.get('group', None),
            value=alert.get('value', None),
            status=status_code.parse_status(alert.get('status', None)),
            severity=severity_code.parse_severity(alert.get('severity', None)),
            previous_severity=severity_code.parse_severity(alert.get('previousSeverity', None)),
            environment=alert.get('environment', None),
            service=alert.get('service', None),
            text=alert.get('text', None),
            event_type=alert.get('type', None),
            tags=alert.get('tags', None),
            origin=alert.get('origin', None),
            repeat=alert.get('repeat', None),
            duplicate_count=alert.get('duplicateCount', None),
            threshold_info=alert.get('thresholdInfo', None),
            summary=alert.get('summary', None),
            timeout=alert.get('timeout', None),
            alertid=alert.get('id', None),
            last_receive_id=alert.get('lastReceiveId', None),
            create_time=alert.get('createTime', None),
            expire_time=alert.get('expireTime', None),
            receive_time=alert.get('receiveTime', None),
            last_receive_time=alert.get('lastReceiveTime', None),
            trend_indication=alert.get('trendIndication', None),
            raw_data=alert.get('rawData', None),
            more_info=alert.get('moreInfo', None),
            graph_urls=alert.get('graphUrls', None),
        )

    def transform_alert(self, trapoid=None, facility=None, level=None, **kwargs):

        if not os.path.exists(CONF.yaml_config):
            return

        suppress = False

        try:
            conf = yaml.load(open(CONF.yaml_config))
            LOG.info('Loaded %d transformer configurations OK', len(conf))
        except Exception, e:
            LOG.error('Failed to load transformer configuration %s: %s', CONF.yaml_config, e)
            return

        for c in conf:
            LOG.debug('YAML config: %s', c)

            match = None
            pattern = None

            if self.get_type() == 'snmptrapAlert' and trapoid and c.get('trapoid'):
                match = re.match(c['trapoid'], trapoid)
                pattern = trapoid
            elif self.get_type() == 'syslogAlert' and facility and level and c.get('priority'):
                match = fnmatch.fnmatch('%s.%s' % (facility, level), c['priority'])
                pattern = c['priority']
            elif c.get('match'):
                try:
                    match = all(item in self.__dict__.items() for item in c['match'].items())
                    pattern = c['match'].items()
                except AttributeError:
                    pass

            if match:
                LOG.debug('Matched %s for %s', pattern, self.get_type())

                # 1. Simple substitutions
                if 'event' in c:
                    self.event = c['event']
                if 'resource' in c:
                    self.resource = c['resource']
                if 'severity' in c:
                    self.severity = c['severity']
                if 'group' in c:
                    self.group = c['group']
                if 'value' in c:
                    self.value = c['value']
                if 'text' in c:
                    self.text = c['text']
                if 'environment' in c:
                    self.environment = c['environment']
                if 'service' in c:
                    self.service = c['service']
                if 'tags' in c:
                    self.tags = c['tags']
                if 'correlate' in c:
                    self.correlate = c['correlate']
                if 'threshold_info' in c:
                    self.threshold_info = c['threshold_info']
                if 'summary' in c:
                    self.summary = c['summary']
                if 'timeout' in c:
                    self.timeout = c['timeout']

                # 2. Complex transformations
                if 'parser' in c:
                    LOG.debug('Loading parser %s', c['parser'])

                    context = kwargs
                    context.update(self.__dict__)

                    try:
                        exec(open('%s/%s.py' % (CONF.parser_dir, c['parser']))) in globals(), context
                        LOG.info('Parser %s/%s exec OK', CONF.parser_dir, c['parser'])
                    except Exception, e:
                        LOG.warning('Parser %s failed: %s', c['parser'], e)

                    for k, v in context.iteritems():
                        if hasattr(self, k):
                            setattr(self, k, v)

                    if 'suppress' in context:
                        suppress = context['suppress']

                # 3. Suppress based on results of 1 or 2
                if 'suppress' in c:
                    suppress = suppress or c['suppress']

                break

        return suppress

    def translate(self, mappings):

        LOG.debug('Translate alert using mappings: %s', mappings)

        for k, v in mappings.iteritems():
            LOG.debug('translate %s -> %s', k, v)
            self.event = self.event.replace(k, v)
            self.resource = self.resource.replace(k, v)
            self.severity = self.severity.replace(k, v)
            self.group = self.group.replace(k, v)
            self.value = self.value.replace(k, v)
            self.text = self.text.replace(k, v)
            self.environment[:] = [e.replace(k, v) for e in self.environment]
            self.service[:] = [s.replace(k, v) for s in self.service]

            if self.tags is not None:
                self.tags[:] = [t.replace(k, v) for t in self.tags]
            if self.correlate is not None:
                self.correlate[:] = [c.replace(k, v) for c in self.correlate]
            if self.threshold_info is not None:
                self.threshold_info = self.threshold_info.replace(k, v)
            if self.summary is not None:
                self.summary = self.summary.replace(k, v)
