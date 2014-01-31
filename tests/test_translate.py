
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

from alerta.common.alert import Alert, status_code, severity_code


class TestAlert(unittest.TestCase):
    """
    Ensures Alert class is working as expected.
    """

    def setUp(self):
        """
        sets stuff up
        """
        self.RESOURCE = 'router55'
        self.EVENT = 'event'
        self.TEXT = 'foo is $f, bar was $B'
        self.TAGS = {'Foo': '--$f--', 'Bar': '$b'}

        self.trapvars = {
            '$f': 'foo',
            '$b': 'bar',
            '$B': 'baz'
        }

    def test_alert_translate(self):
        """
        Ensure a valid alert is created with some assigned values
        """
        alert = Alert(self.RESOURCE, self.EVENT, text=self.TEXT, tags=self.TAGS)

        alert.translate_alert(self.trapvars)

        self.assertEquals(alert.text, 'foo is foo, bar was baz')
        self.assertEquals(alert.tags, {'Foo': '--foo--', 'Bar': 'bar'})

if __name__ == '__main__':
    unittest.main()
