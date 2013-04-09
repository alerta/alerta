#!/usr/bin/env python

import os
import sys

possible_topdir = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                                os.pardir,
                                                os.pardir))
if os.path.exists(os.path.join(possible_topdir, 'alerta', '__init__.py')):
    sys.path.insert(0, possible_topdir)

from alerta.alert import Heartbeat
from alerta.common import log as logging
from alerta.common import config

LOG = logging.getLogger(__name__)
CONF = config.CONF


# TODO(nsatterl): make this a nose test
if __name__ == '__main__':
    config.parse_args(sys.argv[1:])
    logging.setup('alerta')
    hb1 = Heartbeat('myprog/mycompute', '1.0.0')
    print hb1
    print repr(hb1)

    print hb1.origin

    hb2 = Heartbeat(origin='blah', version='2.0.1', heartbeatid='1234')
    print hb2
    print repr(hb2)

