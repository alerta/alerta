#!/usr/bin/env python

import os
import sys

# If ../nova/__init__.py exists, add ../ to Python search path, so that
# it will override what happens to be installed in /usr/(local/)lib/python...
possible_topdir = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                                os.pardir,
                                                os.pardir))
if os.path.exists(os.path.join(possible_topdir, 'alerta', '__init__.py')):
    sys.path.insert(0, possible_topdir)

from alerta.common.daemon import Daemon
from alerta.common import log as logging
from alerta.common import config


__program__ = 'test-daemon'


if __name__ == '__main__':

    config.parse_args(sys.argv)
    logging.setup('test-daemon')
    LOG = logging.getLogger('test-daemon')

    LOG.debug('debug mesg')

    LOG.info("this is an INFO message")

    print "Initialiasing %s" % __program__
    daemon = Daemon(__program__, pidfile='/tmp/pidfile')

    LOG.warning("starting daemon")

    print "Starting %s daemon..." % __program__
    daemon.start()
    daemon.stop()
    print "Daemon stopped"
    # daemon.status()

