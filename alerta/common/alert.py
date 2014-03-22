
import os
import sys
import time
import datetime
import json
from uuid import uuid4
import re
import fnmatch
import yaml

from email import utils

from alerta.common import log as logging
from alerta.common import config
from alerta.common import status_code, severity_code
from alerta.common.utils import DateEncoder

LOG = logging.getLogger(__name__)
CONF = config.CONF

prog = os.path.basename(sys.argv[0])


class Alert(object):

    alert_opts = {
        'yaml_config': '/etc/alerta/%s.yaml' % prog,
        'parser_dir': '/etc/alerta/parsers',
    }

    def __init__(self, resource, event, environment=None, severity=severity_code.NORMAL, correlate=None,
                 status=status_code.UNKNOWN, service=None, group=None, value=None, text=None, tags=None,
                 attributes={}, origin=None, event_type=None, create_time=None, timeout=86400, raw_data=None):

        config.register_opts(Alert.alert_opts)

        prog = os.path.basename(sys.argv[0])

        if not resource:
            raise ValueError('Missing mandatory value for resource')
        if not event:
            raise ValueError('Missing mandatory value for event')
        if any(['.' in key for key in attributes.keys()]) or any(['$' in key for key in attributes.keys()]):
            raise ValueError('Attribute keys must not contain "." or "$"')

        self.id = str(uuid4())
        self.resource = resource
        self.event = event
        self.environment = environment or ""
        self.severity = severity
        self.correlate = correlate or list()
        if correlate and event not in correlate:
            self.correlate.append(event)
        self.status = status
        self.service = service or list()
        self.group = group or 'Misc'
        self.value = value or 'n/a'
        self.text = text or ""
        self.tags = tags or list()
        self.attributes = attributes or dict()
        self.origin = origin or '%s/%s' % (prog, os.uname()[1])
        self.event_type = event_type or 'exceptionAlert'
        self.create_time = create_time or datetime.datetime.utcnow()
        self.receive_time = None
        self.timeout = timeout or CONF.global_timeout
        self.raw_data = raw_data

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
            'resource': self.resource,
            'event': self.event,
            'environment': self.environment,
            'severity': self.severity,
            'correlate': self.correlate,
            'status': self.status,
            'service': self.service,
            'group': self.group,
            'value': self.value,
            'text': self.text,
            'tags': self.tags,
            'attributes': self.attributes,
            'origin': self.origin,
            'type': self.event_type,
            'createTime': self.create_time,
            'timeout': self.timeout,
            'rawData': self.raw_data
        }

    def get_type(self):
        return self.event_type

    def receive_now(self):
        self.receive_time = datetime.datetime.utcnow()

    def __repr__(self):
        return 'Alert(id=%r, environment=%r, resource=%r, event=%r, severity=%r, status=%r)' % (
            self.id, self.environment, self.resource, self.event, self.severity, self.status)

    def __str__(self):
        return json.dumps(self.get_body(), cls=DateEncoder, indent=4)

    @staticmethod
    def parse_alert(alert):

        try:
            alert = json.loads(alert)
        except ValueError, e:
            LOG.error('Could not parse alert - %s: %s', e, alert)
            raise

        for k, v in alert.iteritems():
            if k in ['createTime', 'receiveTime', 'lastReceiveTime', 'expireTime']:
                try:
                    alert[k] = datetime.datetime.strptime(v, '%Y-%m-%dT%H:%M:%S.%fZ')
                except ValueError, e:
                    LOG.error('Could not parse date time string: %s', e)
                    raise

        return Alert(
            resource=alert.get('resource', None),
            event=alert.get('event', None),
            environment=alert.get('environment', None),
            severity=severity_code.parse_severity(alert.get('severity', severity_code.NORMAL)),
            correlate=alert.get('correlate', None),
            status=status_code.parse_status(alert.get('status', status_code.UNKNOWN)),
            service=alert.get('service', list()),
            group=alert.get('group', None),
            value=alert.get('value', None),
            text=alert.get('text', None),
            tags=alert.get('tags', list()),
            attributes=alert.get('attributes', dict()),
            origin=alert.get('origin', None),
            event_type=alert.get('type', None),
            create_time=alert.get('createTime', None),
            timeout=alert.get('timeout', None),
            raw_data=alert.get('rawData', None),
        )

    def transform_alert(self, trapoid=None, facility=None, level=None, **kwargs):
        """
        Transforms alert based on configuration contained in YAML file.
        """

        LOG.info('Transform alert %s using %s', self.id, CONF.yaml_config)

        if not os.path.exists(CONF.yaml_config):
            return

        suppress = False

        try:
            conf = yaml.load(open(CONF.yaml_config))
            LOG.info('Loaded %d transformer configurations OK', len(conf))
        except Exception, e:
            LOG.error('Failed to load transformer configuration %s: %s', CONF.yaml_config, e)
            raise RuntimeError

        for c in conf:
            LOG.debug('YAML config: %s', c)

            match = None
            pattern = None

            if self.event_type == 'snmptrapAlert' and trapoid and c.get('trapoid'):
                match = re.match(c['trapoid'], trapoid)
                pattern = trapoid
            elif self.event_type == 'syslogAlert' and facility and level and c.get('priority'):
                match = fnmatch.fnmatch('%s.%s' % (facility, level), c['priority'])
                pattern = c['priority']
            elif c.get('match'):
                try:
                    match = all(item in self.__dict__.items() for item in c['match'].items())
                    pattern = c['match'].items()
                except AttributeError:
                    pass

            if match:
                LOG.debug('Matched %s for %s', pattern, self.event_type)

                # 1. Simple substitutions
                if 'resource' in c:
                    self.resource = c['resource']
                if 'event' in c:
                    self.event = c['event']
                if 'environment' in c:
                    self.environment = c['environment']
                if 'severity' in c:
                    self.severity = c['severity']
                if 'correlate' in c:
                    self.correlate = c['correlate']
                if 'status' in c:
                    self.correlate = c['status']
                if 'service' in c:
                    self.service = c['service']
                if 'group' in c:
                    self.group = c['group']
                if 'value' in c:
                    self.value = c['value']
                if 'text' in c:
                    self.text = c['text']
                if 'tags' in c:
                    self.tags.append(c['tags'])  # join tags
                if 'attributes' in c:
                    self.attributes.update(c['attributes'])  # merge attributes
                if 'origin' in c:
                    self.timeout = c['origin']
                if 'event_type' in c:
                    self.timeout = c['event_type']
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
                        raise RuntimeError

                    for k, v in context.iteritems():
                        if hasattr(self, k):
                            setattr(self, k, v)

                    if 'suppress' in context:
                        suppress = context['suppress']

                # 3. Suppress based on results of 1 or 2
                if 'suppress' in c:
                    suppress = suppress or c['suppress']

        return suppress


class AlertDocument(object):

    def __init__(self, id, resource, event, environment, severity, correlate, status, service, group, value, text,
                 tags, attributes, origin, event_type, create_time, timeout, raw_data, duplicate_count, repeat,
                 previous_severity, trend_indication, receive_time, last_receive_id, last_receive_time, history):

        self.id = id
        self.resource = resource
        self.event = event
        self.environment = environment or ""
        self.severity = severity
        self.correlate = correlate or list()
        self.status = status
        self.service = service or list()
        self.group = group or 'Misc'
        self.value = value or 'n/a'
        self.text = text or ""
        self.tags = tags or list()
        self.attributes = attributes or dict()
        self.origin = origin or '%s/%s' % (prog, os.uname()[1])
        self.event_type = event_type or 'exceptionAlert'
        self.create_time = create_time or datetime.datetime.utcnow()
        self.timeout = timeout or CONF.global_timeout
        self.raw_data = raw_data

        self.duplicate_count = duplicate_count
        self.repeat = repeat
        self.previous_severity = previous_severity
        self.trend_indication = trend_indication
        self.receive_time = receive_time
        self.last_receive_id = last_receive_id
        self.last_receive_time = last_receive_time
        self.history = history

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

    def get_date(self, attr, fmt):

        if hasattr(self, attr):
            if fmt == 'local':
                return getattr(self, attr).astimezone(self.tz).strftime('%Y/%m/%d %H:%M:%S')
            elif fmt == 'iso' or fmt == 'iso8601':
                return getattr(self, attr).replace(microsecond=0).isoformat() + ".%03dZ" % (getattr(self, attr).microsecond // 1000)
            elif fmt == 'rfc' or fmt == 'rfc2822':
                return utils.formatdate(time.mktime(getattr(self, attr).timetuple()))
            elif fmt == 'short':
                return getattr(self, attr).astimezone(self.tz).strftime('%a %d %H:%M:%S')
            elif fmt == 'epoch':
                return time.mktime(getattr(self, attr).timetuple())
            elif fmt == 'raw':
                return getattr(self, attr)
            else:
                raise ValueError("Unknown date format %s" % fmt)
        else:
            return ValueError("Attribute %s not a date" % attr)

    def get_body(self):

        return {
            'id': self.id,
            'resource': self.resource,
            'event': self.event,
            'environment': self.environment,
            'severity': self.severity,
            'correlate': self.correlate,
            'status': self.status,
            'service': self.service,
            'group': self.group,
            'value': self.value,
            'text': self.text,
            'tags': self.tags,
            'attributes': self.attributes,
            'origin': self.origin,
            'type': self.event_type,
            'createTime': self.create_time,
            'timeout': self.timeout,
            'rawData': self.raw_data,
            'duplicateCount': self.duplicate_count,
            'repeat': self.repeat,
            'previousSeverity': self.previous_severity,
            'trendIndication': self.trend_indication,
            'receiveTime': self.receive_time,
            'lastReceiveId': self.last_receive_id,
            'lastReceiveTime': self.last_receive_time,
            'history': self.history
        }

    def __repr__(self):
        return 'AlertDocument(id=%r, environment=%r, resource=%r, event=%r, severity=%r, status=%r)' % (
            self.id, self.environment, self.resource, self.event, self.severity, self.status)

    def __str__(self):
        return json.dumps(self.get_body(), cls=DateEncoder, indent=4)

    @staticmethod
    def parse_alert(alert):

        try:
            alert = json.loads(alert)
        except ValueError, e:
            LOG.error('Could not parse alert - %s: %s', e, alert)
            raise

        for k, v in alert.iteritems():
            if k in ['createTime', 'receiveTime', 'lastReceiveTime', 'expireTime']:
                try:
                    alert[k] = datetime.datetime.strptime(v, '%Y-%m-%dT%H:%M:%S.%fZ')
                except ValueError, e:
                    LOG.error('Could not parse date time string: %s', e)
                    raise

        return AlertDocument(
            id=alert.get('id', None),
            resource=alert.get('resource', None),
            event=alert.get('event', None),
            environment=alert.get('environment', None),
            severity=severity_code.parse_severity(alert.get('severity', severity_code.NORMAL)),
            correlate=alert.get('correlate', None),
            status=status_code.parse_status(alert.get('status', status_code.UNKNOWN)),
            service=alert.get('service', list()),
            group=alert.get('group', None),
            value=alert.get('value', None),
            text=alert.get('text', None),
            tags=alert.get('tags', list()),
            attributes=alert.get('attributes', dict()),
            origin=alert.get('origin', None),
            event_type=alert.get('type', None),
            create_time=alert.get('createTime', None),
            timeout=alert.get('timeout', None),
            raw_data=alert.get('rawData', None),
            duplicate_count=alert.get('duplicateCount', None),
            repeat=alert.get('repeat', None),
            previous_severity=alert.get('previousSeverity', None),
            trend_indication=alert.get('trendIndication', None),
            receive_time=alert.get('receiveTime', None),
            last_receive_id=alert.get('lastReceiveId', None),
            last_receive_time=alert.get('lastReceiveTime', None),
            history=alert.get('history', None)
        )
