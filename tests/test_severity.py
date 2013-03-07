import os
import sys

possible_topdir = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                                os.pardir,
                                                os.pardir))
if os.path.exists(os.path.join(possible_topdir, 'alerta', '__init__.py')):
    sys.path.insert(0, possible_topdir)

from alerta.alert import severity, status

# while True:
#     s = raw_input('severity?')
#     status = None
#     print '%s' % (severity.parse_severity(s))
#     print severity.MAJOR, severity.MAJOR_SEV_CODE
#     print status.OPEN, status.OPEN_STATUS_CODE

transition = [
    [severity.UNKNOWN, severity.NORMAL, status.CLOSED],
    [severity.NORMAL, severity.NORMAL, status.CLOSED],
    [severity.NORMAL, severity.UNKNOWN, status.UNKNOWN],
    [severity.UNKNOWN, severity.WARNING, status.OPEN],
    [severity.UNKNOWN, severity.MINOR, status.OPEN],
    [severity.UNKNOWN, severity.MAJOR, status.OPEN],
    [severity.UNKNOWN, severity.CRITICAL, status.OPEN],

    [severity.CRITICAL, severity.MAJOR, status.OPEN],
    [severity.CRITICAL, severity.MINOR, status.OPEN],
    [severity.CRITICAL, severity.WARNING, status.OPEN],
    [severity.CRITICAL, severity.NORMAL, status.CLOSED],
    [severity.CRITICAL, severity.UNKNOWN, status.UNKNOWN],

    [severity.CRITICAL, severity.CRITICAL, status.OPEN],
    [severity.MAJOR, severity.WARNING, status.OPEN],
    [severity.WARNING, severity.NORMAL, status.CLOSED],
    [severity.UNKNOWN, severity.UNKNOWN, status.UNKNOWN],
    [severity.DEBUG, severity.AUTH, status.OPEN],
    [severity.DEBUG, severity.INDETERMINATE, status.OPEN],
]

for previous, current, expected in transition:
    print '%s -> %s => %s %s' % (previous, current,
                                 severity.status_from_severity(previous, current),
                                 severity.status_from_severity(previous, current) == expected)
