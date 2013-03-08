#!/usr/bin/env python

import os
import sys
import time

possible_topdir = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                                os.pardir,
                                                os.pardir))
if os.path.exists(os.path.join(possible_topdir, 'alerta', '__init__.py')):
    sys.path.insert(0, possible_topdir)

from alerta.common import config
from alerta.common import log as logging
from alerta.common.tokens import LeakyBucket

LOG = logging.getLogger('alerta.syslog')
CONF = config.CONF

Version = 'alpha'


def main():

    leaky = LeakyBucket(10, rate=3)
    #leaky = LeakyBucket()
    leaky.start()

    try:
        print leaky.get_count(), leaky.get_token(), time.sleep(1)
        print leaky.get_count(), leaky.get_token(), time.sleep(1)
        print leaky.get_count(), leaky.get_token(), time.sleep(1)
        print leaky.get_count(), leaky.get_token(), time.sleep(1)
        print leaky.get_count(), leaky.get_token(), time.sleep(1)
        print leaky.get_count(), leaky.get_token(), time.sleep(1)
        print leaky.get_count(), leaky.get_token(), time.sleep(1)
        print leaky.get_count(), leaky.get_token(), time.sleep(1)
        print leaky.get_count(), leaky.get_token(), time.sleep(1)
        print leaky.get_count(), leaky.get_token(), time.sleep(1)
        print leaky.get_count(), leaky.get_token(), time.sleep(1)
        print leaky.get_count(), leaky.get_token(), time.sleep(1)
        print leaky.get_count(), leaky.get_token(), time.sleep(1)
        print leaky.get_count(), leaky.get_token(), time.sleep(1)
        print leaky.get_count(), leaky.get_token(), time.sleep(1)
        print leaky.get_count(), leaky.get_token(), time.sleep(1)

        time.sleep(5)

        print leaky.get_count(), leaky.get_token(), time.sleep(1)
        print leaky.get_count(), leaky.get_token(), time.sleep(1)
        print leaky.get_count(), leaky.get_token(), time.sleep(1)
        print leaky.get_count(), leaky.get_token(), time.sleep(1)
        print leaky.get_count(), leaky.get_token(), time.sleep(1)

    except (KeyboardInterrupt, SystemExit):
        leaky.shutdown()

    if leaky.is_alive:
        leaky.shutdown()

    print 'bye!'


if __name__ == '__main__':
    config.parse_args(sys.argv[1:], version=Version)
    logging.setup('alerta')
    main()