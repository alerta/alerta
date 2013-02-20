#!/usr/bin/env python

import os
import sys

from logging import getLogger, basicConfig

# If ../nova/__init__.py exists, add ../ to Python search path, so that
# it will override what happens to be installed in /usr/(local/)lib/python...
possible_topdir = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                                os.pardir,
                                                os.pardir))
if os.path.exists(os.path.join(possible_topdir, 'alerta', '__init__.py')):
    sys.path.insert(0, possible_topdir)

from alerta.common import log as logging
from alerta.common import config
from alerta.common.daemon import Daemon

__program__ = 'test-daemon'


if __name__ == '__main__':

    config.parse_args(sys.argv, version='1.1')
    logging.setup('alert-syslog')
    LOG = logging.getLogger('alert-syslog')
    daemon = Daemon(__program__, pidfile='/tmp/pidfile')
    daemon.start()
    daemon.stop()

