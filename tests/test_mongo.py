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

from alerta.common import log as logging, severity_code
from alerta.common import config
from alerta.server.database import Mongo
from alerta.alert import Alert

LOG = logging.getLogger('alerta')
LOG = logging.getLogger(__name__)
CONF = config.CONF

print CONF

config.parse_args(['--use-stderr', '--debug'])
logging.setup('alerta')
db = Mongo()

#print db.save_alert({''})
alert3 = Alert('router55', 'Node_Down', severity=severity_code.INDETERMINATE, value='FAILED', timeout=600,
               environment=['PROD'], receive_time="2013-02-23T09:18:05.303Z", last_receive_time="2013-02-23T09:18:05.303Z",
               service=['Network', 'Common'], tags=['london', 'location:london', 'dc:location=london'],
               text="Node is not responding via ping.", origin="test3", correlate=['Node_Up', 'Node_Down'],
               event_type='myAlert', trend_indication='moreSevere')
print alert3
print alert3.get_id()

print alert3.get_header()
print alert3.get_body()

print 'Saving alert...'
print db.save_alert(alert3)


print 'Get alert...'
print db.get_alert('PROD', 'router55', 'Node_Down', 'Indeterminate')

print 'Check for duplicate...'
print db.is_duplicate('PROD', 'router55', 'Node_Down', 'Indeterminate')
print db.is_duplicate('PROD', 'res1', 'event1', 'critical')
