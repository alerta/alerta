
import datetime
import json

from uuid import uuid4

from alerta.alert import severity


class Alert(object):

    def __init__(self, resource, event, correlate=[], group='Misc',
                 value=None, severity=severity.NORMAL, environment=['PROD'],
                 service=[], text=None, tags=[], summary=None, origin=None,
                 thresholdInfo=None, timeout=3600
    ):

        if not summary:
            summary = '%s - %s %s is %s on %s %s' % (','.join(environment), severity, event,
                                                     value, ','.join(service), resource)

        self.alert = {
            'id': str(uuid4()),
            'resource': resource,
            'event': event,
            'correlatedEvents': correlate,
            'group': group,
            'value': value,
            'severity': severity,
            'environment': environment,
            'service': service,
            'text': text,
            'tags': tags,
            'summary': summary,
            'createTime': datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + 'Z',
            'origin': origin,
            'thresholdInfo': thresholdInfo,
            'timeout': timeout,
            }

    def __str__(self):
        return json.dumps(self.alert, indent=4)

    def __getattr__(self, item):
        # TODO(nsatterl): why?
        pass

    def send(self):

        pass

# TODO(nsatterl): make this a nose test
if __name__ == '__main__':
    alert1 = Alert('host555', 'ping_fail')
    print alert1

    alert2 = Alert('http://www.guardian.co.uk', 'HttpResponseSlow', ['HttpResponseOK','HttpResponseSlow'],
                   'HTTP', '505 ms', severity.CRITICAL, ['RELEASE','QA'],
                   ['gu.com'], 'The website is slow to respond.', ['web','dc1','user'],
                   'python-webtest', 'n/a', 1200)
    print alert2

    alert3 = Alert('router55', 'Node_Down', severity=severity.INDETERMINATE, value='FAILED', timeout=600,
                   service=['Network', 'Common'], tags=['london', 'location:london', 'dc:location=london'],
                   text="Node is not responding via ping.", origin="test3", correlate=['Node_Up', 'Node_Down'])
    print alert3