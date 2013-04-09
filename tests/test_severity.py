import os
import sys

possible_topdir = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                                os.pardir,
                                                os.pardir))
if os.path.exists(os.path.join(possible_topdir, 'alerta', '__init__.py')):
    sys.path.insert(0, possible_topdir)

from alerta.alert import severity_code, status_code

# while True:
#     s = raw_input('severity?')
#     status = None
#     print '%s' % (severity.parse_severity(s))
#     print severity.MAJOR, severity.MAJOR_SEV_CODE
#     print status.OPEN, status.OPEN_STATUS_CODE

transition = [
    [severity_code.UNKNOWN, severity_code.NORMAL, status_code.CLOSED],
    [severity_code.NORMAL, severity_code.NORMAL, status_code.CLOSED],
    [severity_code.NORMAL, severity_code.UNKNOWN, status_code.UNKNOWN],
    [severity_code.UNKNOWN, severity_code.WARNING, status_code.OPEN],
    [severity_code.UNKNOWN, severity_code.MINOR, status_code.OPEN],
    [severity_code.UNKNOWN, severity_code.MAJOR, status_code.OPEN],
    [severity_code.UNKNOWN, severity_code.CRITICAL, status_code.OPEN],

    [severity_code.CRITICAL, severity_code.MAJOR, status_code.OPEN],
    [severity_code.CRITICAL, severity_code.MINOR, status_code.OPEN],
    [severity_code.CRITICAL, severity_code.WARNING, status_code.OPEN],
    [severity_code.CRITICAL, severity_code.NORMAL, status_code.CLOSED],
    [severity_code.CRITICAL, severity_code.UNKNOWN, status_code.UNKNOWN],

    [severity_code.CRITICAL, severity_code.CRITICAL, status_code.OPEN],
    [severity_code.MAJOR, severity_code.WARNING, status_code.OPEN],
    [severity_code.WARNING, severity_code.NORMAL, status_code.CLOSED],
    [severity_code.UNKNOWN, severity_code.UNKNOWN, status_code.UNKNOWN],
    [severity_code.DEBUG, severity_code.AUTH, status_code.OPEN],
    [severity_code.DEBUG, severity_code.INDETERMINATE, status_code.OPEN],
]

for previous, current, expected in transition:
    print '%s -> %s => %s %s' % (previous, current,
                                 severity_code.status_from_severity(previous, current),
                                 severity_code.status_from_severity(previous, current) == expected)
