
import os
import sys
import unittest

import datetime

# If ../alerta/__init__.py exists, add ../ to Python search path, so that
# it will override what happens to be installed in /usr/(local/)lib/python...
possible_topdir = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                                os.pardir,
                                                os.pardir))
if os.path.exists(os.path.join(possible_topdir, 'alerta', '__init__.py')):
    sys.path.insert(0, possible_topdir)

from alerta.common import status_code, severity_code
from alerta.common.alert import Alert, AlertDocument


class TestAlert(unittest.TestCase):
    """
    Ensures Alert class is working as expected.
    """

    def setUp(self):
        """
        sets stuff up
        """
        self.RESOURCE = 'router55'
        self.EVENT = 'Node_Down'
        self.CORRELATE = ['Node_Down', 'Node_Up']
        self.GROUP = 'Network'
        self.VALUE = 'ping failed'
        self.STATUS = status_code.OPEN
        self.SEVERITY = severity_code.MAJOR
        self.PREVIOUS_SEVERITY = severity_code.UNKNOWN
        self.ENVIRONMENT = ['PROD']
        self.SERVICE = ['Common']
        self.TEXT = 'Node is not responding to ping'
        self.EVENT_TYPE = 'exceptionAlert'
        self.TAGS = ['location:london', 'vendor:cisco']
        self.ORIGIN = 'test_alert'
        self.REPEAT = False
        self.DUPLICATE_COUNT = 0
        self.THRESHOLD_INFO = 'n/a'
        self.SUMMARY = 'PROD - major Node_Down is ping failed on Common router55'
        self.TIMEOUT = 86400
        self.ALERTID = 'random-uuid'
        self.LAST_RECEIVE_ID = 'random-uuid'
        self.CREATE_TIME = datetime.datetime.utcnow()
        self.EXPIRE_TIME = self.CREATE_TIME + datetime.timedelta(self.TIMEOUT)
        self.RECEIVE_TIME = datetime.datetime.utcnow()
        self.TREND_INDICATION = 'moreSevere'
        self.RAW_DATA = 'lots of raw text'
        self.MORE_INFO = ''
        self.GRAPH_URLS = list()
        self.HISTORY = [{
                        "event": self.EVENT,
                        "severity": self.SEVERITY,
                        "text": self.TEXT,
                        "value": self.VALUE,
                        "id": self.ALERTID,
                        "receiveTime": self.RECEIVE_TIME,
                        "createTime": self.CREATE_TIME
                        }]

    def test_alertdoc(self):
        """
        Ensure a valid alert document is created with all assigned values
        """

        alert = AlertDocument(id=self.ALERTID, resource=self.RESOURCE, event=self.EVENT, environment=self.ENVIRONMENT,
                      severity=self.SEVERITY, correlate=self.CORRELATE, status=self.STATUS, service=self.SERVICE, group=self.GROUP,
                      value=self.VALUE, text=self.TEXT, tags=self.TAGS,
                      attributes={'thresholdInfo': self.THRESHOLD_INFO, 'moreInfo': self.MORE_INFO, 'graphUrls': self.GRAPH_URLS},
                      origin=self.ORIGIN, event_type=self.EVENT_TYPE, create_time=self.CREATE_TIME, timeout=self.TIMEOUT,
                      raw_data=self.RAW_DATA, duplicate_count=self.DUPLICATE_COUNT, repeat=self.REPEAT,
                      previous_severity=self.PREVIOUS_SEVERITY, trend_indication=self.TREND_INDICATION, receive_time=self.RECEIVE_TIME,
                      last_receive_id=self.ALERTID, last_receive_time=self.RECEIVE_TIME, history=self.HISTORY)

        self.assertEquals(alert.resource, self.RESOURCE)
        self.assertEquals(alert.event, self.EVENT)
        self.assertEquals(alert.correlate, self.CORRELATE)
        self.assertEquals(alert.group, self.GROUP)
        self.assertEquals(alert.value, self.VALUE)
        self.assertEquals(alert.status, self.STATUS)
        self.assertEquals(alert.severity, self.SEVERITY)
        self.assertEquals(alert.previous_severity, self.PREVIOUS_SEVERITY)
        self.assertEquals(alert.environment, self.ENVIRONMENT)
        self.assertEquals(alert.service, self.SERVICE)
        self.assertEquals(alert.text, self.TEXT)
        self.assertEquals(alert.event_type, self.EVENT_TYPE)
        self.assertEquals(alert.tags, self.TAGS)
        self.assertEquals(alert.origin, self.ORIGIN)
        self.assertEquals(alert.repeat, self.REPEAT)
        self.assertEquals(alert.duplicate_count, self.DUPLICATE_COUNT)
        self.assertEquals(alert.timeout, self.TIMEOUT)
        self.assertEquals(alert.id, self.ALERTID)
        self.assertEquals(alert.last_receive_id, self.ALERTID)
        self.assertEquals(alert.create_time, self.CREATE_TIME)
        self.assertEquals(alert.receive_time, self.RECEIVE_TIME)
        self.assertEquals(alert.trend_indication, self.TREND_INDICATION)
        self.assertEquals(alert.raw_data, self.RAW_DATA)
        self.assertEquals(alert.history, self.HISTORY)

if __name__ == '__main__':
    unittest.main()
