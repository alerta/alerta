
from alerta.alert import severity, status

while True:
    s = raw_input('severity?')
    status = None
    print '%s' % (severity.parse_severity(s))
    print severity.MAJOR, severity.MAJOR_SEV_CODE
    print status.OPEN, status.OPEN_STATUS_CODE