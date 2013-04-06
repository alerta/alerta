#!/usr/bin/env python

import os
import sys

possible_topdir = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                                os.pardir,
                                                os.pardir))
if os.path.exists(os.path.join(possible_topdir, 'alerta', '__init__.py')):
    sys.path.insert(0, possible_topdir)

from alerta.alert import Alert, severity_code
from alerta.common import log as logging
from alerta.common import config
from alerta.common import dedup

LOG = logging.getLogger(__name__)
CONF = config.CONF


# TODO(nsatterl): make this a nose test
if __name__ == '__main__':
    config.parse_args(sys.argv[1:])
    logging.setup('alerta')
    alert1 = Alert('host555', 'ping_fail')
    print alert1

    alert2 = Alert('http://www.guardian.co.uk', 'HttpResponseSlow', ['HttpResponseOK', 'HttpResponseSlow'],
                   'HTTP', '505 ms', None, severity_code.CRITICAL, None, ['RELEASE', 'QA'],
                   ['gu.com'], 'The website is slow to respond.', 'httpAlert', ['web', 'dc1', 'user'],
                   'python-webtest', False, 0, 'n/a', 1200)
    print alert2

    alert3 = Alert('router55', 'Node_Down', severity=severity_code.INDETERMINATE, value='FAILED', timeout=600,
                   service=['Network', 'Common'], tags=['london', 'location:london', 'dc:location=london'],
                   text="Node is not responding via ping.", origin="test3", correlate=['Node_Up', 'Node_Down'],
                   event_type='myAlert', alertid='1234', raw_data='blah blah blah')
    print alert3

    print repr(alert3)

    print 'transforming...'
    suppress = alert1.transform_alert()
    print 'suppress? %s' % suppress
    print alert1


    # set up local dedup tracker
    dedup = dedup.DeDup()
    print '>>> %s' % dedup

    print 'create new alert...'
    print 'is dup? False=%s' % dedup.is_duplicate(alert1)
    print 'is send? True=%s' % dedup.is_send(alert1, 4)
    dedup.update(alert1)
    print dedup
    print

    print 'create a duplicate alert...'
    print 'is dup? True=%s' % dedup.is_duplicate(alert1)
    print 'is send? False=%s' % dedup.is_send(alert1, 4)
    dedup.update(alert1)
    print dedup
    print

    print 'create another 2 duplicates...'
    dedup.update(alert1)
    dedup.update(alert1)
    print 'is dup? True=%s' % dedup.is_duplicate(alert1)
    print 'is send (every 4)? True=%s' % dedup.is_send(alert1, 4)
    print dedup
    print

    print 'create different alert...'
    print 'is dup? False=%s' % dedup.is_duplicate(alert2)
    print 'is send? True=%s' % dedup.is_send(alert2, 4)
    dedup.update(alert2)
    print dedup
    print


    print 'create alert for new resource...'
    print 'is dup? False=%s' % dedup.is_duplicate(alert3)
    print 'is dup? False=%s' % dedup.is_duplicate(alert3)
    print 'is send? True=%s' % dedup.is_send(alert3, 4)
    print 'is send? True=%s' % dedup.is_send(alert3, 4)
    dedup.update(alert3)
    dedup.update(alert3)
    print 'is dup? True=%s' % dedup.is_duplicate(alert3)
    print 'is dup? True=%s' % dedup.is_duplicate(alert3)
    print 'is send? False=%s' % dedup.is_send(alert3, 4)
    print 'is send? True=%s' % dedup.is_send(alert3, 1)
    print dedup



