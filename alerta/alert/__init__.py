
import os
import sys
import datetime
import json
import yaml
from uuid import uuid4
from __builtin__ import staticmethod

import pytz

from alerta.alert import severity, status
from alerta.common import log as logging
from alerta.common import config
from alerta.common.utils import DateEncoder

_DEFAULT_TIMEOUT = 3600  # default number of seconds before alert is EXPIRED

LOG = logging.getLogger(__name__)
CONF = config.CONF


class Alert(object):
    def __init__(self, resource, event, correlate=None, group='Misc', value=None, status=status.UNKNOWN,
                 severity=severity.NORMAL, previous_severity=None, environment=None, service=None,
                 text=None, event_type='exceptionAlert', tags=None, origin=None, repeat=False, duplicate_count=0,
                 threshold_info='n/a', summary=None, timeout=_DEFAULT_TIMEOUT, alertid=None, last_receive_id=None,
                 create_time=None, expire_time=None, receive_time=None, last_receive_time=None, trend_indication=None,
                 raw_data=None):

        prog = os.path.basename(sys.argv[0])

        self.alertid = alertid or str(uuid4())

        correlate = correlate or list()
        environment = environment or ['PROD']
        service = service or list()
        tags = tags or list()

        create_time = create_time or datetime.datetime.utcnow()
        expire_time = expire_time or create_time + datetime.timedelta(seconds=timeout)

        self.summary = summary or '%s - %s %s is %s on %s %s' % (
            ','.join(environment), severity, event, value, ','.join(service), resource)

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
            'previousSeverity': previous_severity or 'UNKNOWN', # severity.UNKNOWN,
            'environment': environment,
            'service': service,
            'text': text,
            'type': event_type,
            'tags': tags,
            'summary': self.summary,
            'createTime': create_time,
            'origin': origin or '%s/%s' % (prog, os.uname()[1]),
            'thresholdInfo': threshold_info,
            'timeout': timeout,
            'expireTime': expire_time,
            'repeat': repeat,
            'duplicateCount': duplicate_count,
            'rawData': raw_data,
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
        return json.dumps(self.alert, cls=DateEncoder, indent=4)

    def get_id(self, short=False):
        if short is True:
            return self.alertid.split('-')[0]
        else:
            return self.alertid

    def get_header(self):
        return self.header

    def get_body(self):
        return self.alert

    def get_type(self):
        return self.header['type']

    def receive_now(self):
        self.alert['receiveTime'] = datetime.datetime.utcnow()

    def ack(self):
        # TODO(nsatterl): alert.ack()
        raise NotImplementedError

    def delete(self):
        # TODO(nsatterl): alert.delete()
        raise NotImplementedError

    def tag(self, tags):
        # TODO(nsatterl): alert.tag(tags)
        raise NotImplementedError

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
        #         alert[k] = time.replace(tzinfo=pytz.utc)   # TODO(nsatterl): test timezone stuff

        return Alert(
            resource=alert.get('resource', None),
            event=alert.get('event', None),
            correlate=alert.get('correlatedEvents', None),
            group=alert.get('group', None),
            value=alert.get('value', None),
            status=status.parse_status(alert.get('status', None)),
            severity=severity.parse_severity(alert.get('severity', None)),
            previous_severity=severity.parse_severity(alert.get('previousSeverity', None)),
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
        )

    @staticmethod
    def transform_alert(alert):

        resource = alert.alert.get('resource', None)
        event = alert.alert.get('event', None)
        correlate = alert.alert.get('correlatedEvents', None)
        group = alert.alert.get('group', None)
        value = alert.alert.get('value', None)
        status = alert.alert.get('status', None)
        severity = alert.alert.get('severity', None)
        previous_severity = alert.alert.get('previousSeverity', None)
        environment = alert.alert.get('environment', None)
        service = alert.alert.get('service', None)
        text = alert.alert.get('text', None)
        event_type = alert.alert.get('type', None)
        tags = alert.alert.get('tags', None)
        origin = alert.alert.get('origin', None)
        repeat = alert.alert.get('repeat', None)
        duplicate_count = alert.alert.get('duplicateCount', None)
        threshold_info = alert.alert.get('thresholdInfo', None)
        summary = alert.alert.get('summary', None)
        timeout = alert.alert.get('timeout', None)
        alertid = alert.alert.get('id', None)
        last_receive_id = alert.alert.get('lastReceiveId', None)
        create_time = alert.alert.get('createTime', None)
        expire_time = alert.alert.get('expireTime', None)
        receive_time = alert.alert.get('receiveTime', None)
        last_receive_time = alert.alert.get('lastReceiveTime', None)
        trend_indication = alert.alert.get('trendIndication', None)
        raw_data = alert.alert.get('rawData', None)

        suppress = False

        conf = dict()
        try:
            conf = yaml.load(open(CONF.yaml_config))
            LOG.info('Loaded %d transformer configurations OK', len(conf))
        except Exception, e:
            LOG.error('Failed to load transformer configuration: %s', e)
            #sys.exit(1)

        for c in conf:
            LOG.debug('YAML config: %s', c)
            if all(item in alert.alert.items() for item in c['match'].items()):
                LOG.debug('Matched %s in alert', c['match'])

                if 'parser' in c:
                    LOG.debug('Loading parser %s', c['parser'])
                    try:
                        exec open('%s/%s.py' % (CONF.parser_dir, c['parser'])) in globals(), locals()
                        LOG.info('Parser %s/%s exec OK', CONF.parser_dir, c['parser'])
                    except Exception, e:
                        LOG.warning('Parser %s failed: %s', c['parser'], e)

                if 'event' in c:
                    event = c['event']
                if 'resource' in c:
                    resource = c['resource']
                if 'severity' in c:
                    severity = c['severity']
                if 'group' in c:
                    group = c['group']
                if 'value' in c:
                    value = c['value']
                if 'text' in c:
                    text = c['text']
                if 'environment' in c:
                    environment = c['environment']
                if 'service' in c:
                    service = c['service']
                if 'tags' in c:
                    tags = c['tags']
                if 'correlate' in c:
                    correlate = c['correlate']
                if 'threshold_info' in c:
                    threshold_info = c['threshold_info']
                if 'summary' in c:
                    summary = c['summary']
                if 'timeout' in c:
                    timeout = c['timeout']
                if 'suppress' in c:
                    suppress = c['suppress']
                break

        if suppress:
            LOG.info('Suppressing alert %s', alert.alertid)
            return

        LOG.debug('group = %s', group)

        return Alert(
            resource=resource,
            event=event,
            correlate=correlate,
            group=group,
            value=value,
            status=status,
            severity=severity,
            previous_severity=previous_severity,
            environment=environment,
            service=service,
            text=text,
            event_type=event_type,
            tags=tags,
            origin=origin,
            repeat=repeat,
            duplicate_count=duplicate_count,
            threshold_info=threshold_info,
            summary=summary,
            timeout=timeout,
            alertid=alertid,
            last_receive_id=last_receive_id,
            create_time=create_time,
            expire_time=expire_time,
            receive_time=receive_time,
            last_receive_time=last_receive_time,
            trend_indication=trend_indication,
            raw_data=raw_data,
        )


class Heartbeat(object):

    def __init__(self, origin=None, version='unknown', heartbeatid=None, create_time=None):

        prog = os.path.basename(sys.argv[0])

        self.heartbeatid = heartbeatid or str(uuid4())

        create_time = create_time or datetime.datetime.utcnow()

        self.header = {
            'type': 'Heartbeat',
            'correlation-id': self.heartbeatid,
        }

        self.heartbeat = {
            'id': self.heartbeatid,
            'type': 'Heartbeat',
            'createTime': create_time,
            'origin': origin or '%s/%s' % (prog, os.uname()[1]),
            'version': version,
        }

    def __repr__(self):
        return 'Heartbeat(header=%r, heartbeat=%r)' % (str(self.header), str(self.heartbeat))

    def __str__(self):
        return json.dumps(self.heartbeat, cls=DateEncoder, indent=4)

    def get_id(self):
        return self.heartbeatid

    def get_header(self):
        return self.header

    def get_body(self):
        return self.heartbeat

    def get_type(self):
        return self.header['type']

    def receive_now(self):
        self.heartbeat['receiveTime'] = datetime.datetime.utcnow()

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
            # heartbeat[k] = time.replace(tzinfo=pytz.utc)   # TODO(nsatterl): test timezone stuff

        return Heartbeat(
            origin=heartbeat.get('origin', None),
            version=heartbeat.get('version', None),
            heartbeatid=heartbeat.get('id', None),
            create_time=heartbeat.get('createTime', None),
        )
