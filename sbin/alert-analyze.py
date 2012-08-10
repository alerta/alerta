#!/usr/bin/env python

import time
import rrdtool

thresholdInfo = 'Critical:>:90;Major:>:80;Minor:>:60;Normal:<:60'

SOCKET = 'unix:/var/run/rrdcached/rrdcached.limited.sock'
METRIC = 'fs_util-boot'
RRDFILE = '%s.rrd' % METRIC

info = rrdtool.info(RRDFILE)
print info

end = int(time.time())
start = int(end - 60)
print end
print start

info, ds, data = rrdtool.fetch(RRDFILE, 'AVERAGE', '--daemon', SOCKET, '--start', str(start), '--end', str(end))
print info
print ds
print data
