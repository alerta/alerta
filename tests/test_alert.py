
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

from alerta.alert import Alert
from alerta.app import severity_code, status_code


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

    def test_alert_defaults(self):
        """
        Ensures a valid alert is created with default values
        """
        alert = Alert(self.RESOURCE, self.EVENT)

        self.assertEquals(alert.resource, self.RESOURCE)
        self.assertEquals(alert.event, self.EVENT)
        self.assertEquals(alert.group, 'Misc')
        self.assertEquals(alert.timeout, self.TIMEOUT)

    def test_alert_with_some_values(self):
        """
        Ensure a valid alert is created with some assigned values
        """
        alert = Alert(self.RESOURCE, self.EVENT, severity=self.SEVERITY, environment=self.ENVIRONMENT)

        self.assertEquals(alert.resource, self.RESOURCE)
        self.assertEquals(alert.event, self.EVENT)
        self.assertEquals(alert.severity, self.SEVERITY)
        self.assertEquals(alert.environment, self.ENVIRONMENT)

    def test_alert_receive_now(self):
        """
        Ensure receive time is stamped.
        """
        alert = Alert(self.RESOURCE, self.EVENT, severity=self.SEVERITY, environment=self.ENVIRONMENT)

        alert.receive_now()
        self.assertIsInstance(alert.receive_time, datetime.datetime)


if __name__ == '__main__':
    unittest.main()
