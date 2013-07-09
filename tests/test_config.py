
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

from alerta.common import config


class TestConfig(unittest.TestCase):

    def setUp(self):

        config.parse_args(list())
        self.CONF = config.CONF
        # print self.CONF

        self.CONF_FILE = '/etc/alerta/alerta.conf'
        self.ALERT_TIMEOUT = 86400

    def test_option_defaults(self):

        self.assertEquals(self.CONF.conf_file, self.CONF_FILE)
        self.assertTrue(self.CONF.use_syslog)

    def test_system_defaults(self):
        self.assertEquals(self.CONF.global_timeout, self.ALERT_TIMEOUT)