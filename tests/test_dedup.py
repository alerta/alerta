import os
import sys

possible_topdir = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                                os.pardir,
                                                os.pardir))
if os.path.exists(os.path.join(possible_topdir, 'alerta', '__init__.py')):
    sys.path.insert(0, possible_topdir)

from alerta.common import dedup

# set up local dedup tracker
dedup = dedup.DeDup()
print '>>> %s' % dedup

print 'create new alert...'
print 'is dup? False=%s' % dedup.is_duplicate(['RELEASE'], 'host111', 'node_down', 'critical')
print 'is send? True=%s' % dedup.is_send(['RELEASE'], 'host111', 'node_down', 'critical', 4)
dedup.update(['RELEASE'], 'host111', 'node_down', 'critical')
print dedup
print

print 'create a duplicate alert...'
print 'is dup? True=%s' % dedup.is_duplicate(['RELEASE'], 'host111', 'node_down', 'critical')
print 'is send? False=%s' % dedup.is_send(['RELEASE'], 'host111', 'node_down', 'critical', 4)
dedup.update(['RELEASE'], 'host111', 'node_down', 'critical')
print dedup
print

print 'create another 2 duplicates...'
dedup.update(['RELEASE'], 'host111', 'node_down', 'critical')
dedup.update(['RELEASE'], 'host111', 'node_down', 'critical')
print 'is dup? True=%s' % dedup.is_duplicate(['RELEASE'], 'host111', 'node_down', 'critical')
print 'is send (every 4)? True=%s' % dedup.is_send(['RELEASE'], 'host111', 'node_down', 'critical', 4)
print dedup
print

print 'create different alert...'
print 'is dup? False=%s' % dedup.is_duplicate(['RELEASE'], 'host111', 'node_up', 'critical')
print 'is send? True=%s' % dedup.is_send(['RELEASE'], 'host111', 'node_up', 'critical', 4)
dedup.update(['RELEASE'], 'host111', 'node_up', 'critical')
print dedup
print


print 'create alert for new resource...'
print 'is dup? False=%s' % dedup.is_duplicate(['RELEASE'], 'node7', 'node_down', 'critical')
print 'is dup? False=%s' % dedup.is_duplicate(['PROD'], 'node7', 'node_down', 'critical')
print 'is send? True=%s' % dedup.is_send(['RELEASE'], 'node7', 'node_down', 'critical', 4)
print 'is send? True=%s' % dedup.is_send(['PROD'], 'node7', 'node_down', 'critical', 4)
dedup.update(['RELEASE'], 'node7', 'node_down', 'critical')
dedup.update(['PROD'], 'node7', 'node_down', 'critical')
print 'is dup? True=%s' % dedup.is_duplicate(['RELEASE'], 'node7', 'node_down', 'critical')
print 'is dup? True=%s' % dedup.is_duplicate(['PROD'], 'node7', 'node_down', 'critical')
print 'is send? False=%s' % dedup.is_send(['RELEASE'], 'node7', 'node_down', 'critical', 4)
print 'is send? True=%s' % dedup.is_send(['PROD'], 'node7', 'node_down', 'critical', 1)
print dedup



