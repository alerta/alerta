
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

CONF = config.CONF


class TestConfig(unittest.TestCase):

    def setUp(self):

        self.cli_args = ['--debug', '--pid-dir', '/tmp/test', '--log-file', 'foo']
        config.parse_args(self.cli_args)

        SYS_OPTS = {
            'host': 'host44',
            'port': 55,
            'ack': False,
        }
        config.register_opts(SYS_OPTS)

    def test_cli_options(self):

        self.assertEqual(CONF.debug, True)
        self.assertEqual(CONF.server_threads, 4)
        # self.assertEqual(CONF.pid_dir, '/tmp/test')
        self.assertEqual(CONF.log_file, 'foo')

    def test_sys_options(self):

        self.assertEqual(CONF.host, 'host44')
        self.assertEqual(CONF.port, 55)
        self.assertEqual(CONF.ack, False)
