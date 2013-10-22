
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

        self.TEST_OPTS = {
            'host': 'host44',
            'port': 55,
            'ack': False,
            'locations': ['london', 'paris']
        }

        self.INTER_OPTS = {
            'baz': 'fun',
            'bar': 'Python',
            #'foo': '%(bar)s is %(baz)s!'  # interpolation not supported
        }

    def test_cli_options(self):

        config.parse_args(args=self.cli_args, section='alert-test')

        self.assertEqual(CONF.debug, True)
        self.assertEqual(CONF.server_threads, 4)
        self.assertEqual(CONF.pid_dir, '/tmp/test')
        self.assertEqual(CONF.log_file, 'foo')

    def test_sys_options(self):

        config.register_opts(self.TEST_OPTS, section='alert-test')

        self.assertEqual(CONF.host, 'host44')
        self.assertEqual(CONF.port, 55)
        self.assertEqual(CONF.ack, False)
        self.assertEqual(CONF.locations, ['london', 'paris'])
        self.assertEqual(CONF.global_timeout, 86400)

    def test_interpolation(self):

        config.register_opts(self.INTER_OPTS, section='alert-test')

        #self.assertEqual(CONF.foo, 'Python is fun!')

    def test_config_file(self):

        config.parse_args(args=['--config-file', 'tests/example.conf'], section='alert-test')

        self.assertEqual(CONF.foo, 'baz')
        self.assertEqual(CONF.spam, True)
        self.assertEqual(CONF.ham, 567)
        self.assertEqual(CONF.xyz, ['qux', 'wibble', 'wobble'])

