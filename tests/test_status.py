
import os
import sys
import unittest

# If ../alerta/__init__.py exists, add ../ to Python search path, so that
# it will override what happens to be installed in /usr/(local/)lib/python...
possible_topdir = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                                os.pardir,
                                                os.pardir))
if os.path.exists(os.path.join(possible_topdir, 'alerta', '__init__.py')):
    sys.path.insert(0, possible_topdir)

from alerta.common.alert import status_code, severity_code


class TestStatus(unittest.TestCase):
    """
    Ensures my Alert class is working as expected.
    """

    def setUp(self):
        pass

    def test_status_closed(self):
        """
        When alert Clears or becomes Normal, then status is Closed
        """

        self.assertEquals(severity_code.status_from_severity(severity_code.CRITICAL, severity_code.CLEARED), status_code.CLOSED)
        self.assertEquals(severity_code.status_from_severity(severity_code.WARNING, severity_code.CLEARED), status_code.CLOSED)
        self.assertEquals(severity_code.status_from_severity(severity_code.UNKNOWN, severity_code.NORMAL), status_code.CLOSED)
        self.assertEquals(severity_code.status_from_severity(severity_code.DEBUG, severity_code.CLEARED), status_code.CLOSED)
        self.assertEquals(severity_code.status_from_severity(severity_code.AUTH, severity_code.NORMAL), status_code.CLOSED)

    def test_status_no_change(self):
        """
        When trendIndication is lessSevere, status should not change
        """
        self.assertEquals(severity_code.status_from_severity(severity_code.NORMAL, severity_code.UNKNOWN, status_code.OPEN), status_code.OPEN)

    def test_status_reopen(self):
        """
        When trendIndication is moreSevere, status should be set to Open
        """
        self.assertEquals(severity_code.status_from_severity(severity_code.MINOR, severity_code.MAJOR, status_code.ACK), status_code.OPEN)
        self.assertEquals(severity_code.status_from_severity(severity_code.NORMAL, severity_code.MAJOR, status_code.CLOSED), status_code.OPEN)

if __name__ == '__main__':
    unittest.main()