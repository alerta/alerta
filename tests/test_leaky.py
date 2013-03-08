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

from alerta.common import log as logging
from alerta.common import config
from alerta.common.tokens import LeakyBucket

LOG = logging.getLogger('alerta')
LOG = logging.getLogger(__name__)
CONF = config.CONF


def main():

    leaky = LeakyBucket()
    leaky.start()

    print leaky.get_token()
    print leaky.get_token()
    print leaky.get_token()
    print leaky.get_token()
    print leaky.get_token()
    print leaky.get_token()
    print leaky.get_token()
    print leaky.get_token()
    print leaky.get_token()
    print leaky.get_token()
    print leaky.get_token()
    print leaky.get_token()



if __name__ == '__main__':
    main()