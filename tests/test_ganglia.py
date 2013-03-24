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

from alerta.common.ganglia import Gmetric

g = Gmetric()

g.metric_send("heartbeat", "0", "uint32", "", "zero", 0, 0, "", "", "", 'spoof1:spoof1')
g.metric_send('percent_metric', '100.0', 'float')
g.metric_send('high_med_low', 'HIGH', 'string', spoof='spoof2:spoof2')


