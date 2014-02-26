"""
Possible alert severity codes.

See ITU-T perceived severity model M.3100 and CCITT Rec X.736
http://tools.ietf.org/html/rfc5674
http://www.itu.int/rec/T-REC-M.3100
http://www.itu.int/rec/T-REC-X.736-199201-I

           ITU Perceived Severity      syslog SEVERITY (Name)
           Critical                    1 (Alert)
           Major                       2 (Critical)
           Minor                       3 (Error)
           Warning                     4 (Warning)
           Indeterminate               5 (Notice)
           Cleared                     5 (Notice)
"""
from alerta.common import status_code

CRITICAL_SEV_CODE = 1
MAJOR_SEV_CODE = 2
MINOR_SEV_CODE = 3
WARNING_SEV_CODE = 4
INDETER_SEV_CODE = 5
CLEARED_SEV_CODE = 5
NORMAL_SEV_CODE = 5
INFORM_SEV_CODE = 6
DEBUG_SEV_CODE = 7
AUTH_SEV_CODE = 8
UNKNOWN_SEV_CODE = 9

# NOTE: The display text in single quotes can be changed depending on preference.
# eg. CRITICAL = 'critical' or CRITICAL = 'CRITICAL'

CRITICAL = 'critical'
MAJOR = 'major'
MINOR = 'minor'
WARNING = 'warning'
INDETERMINATE = 'indeterminate'
CLEARED = 'cleared'
NORMAL = 'normal'
INFORM = 'informational'
DEBUG = 'debug'
AUTH = 'security'
UNKNOWN = 'unknown'
NOT_VALID = 'notValid'

ALL = [CRITICAL, MAJOR, MINOR, WARNING, INDETERMINATE, CLEARED, NORMAL, INFORM, DEBUG, AUTH, UNKNOWN, NOT_VALID]

MORE_SEVERE = 'moreSevere'
LESS_SEVERE = 'lessSevere'
NO_CHANGE = 'noChange'

_SEVERITY_MAP = {
    CRITICAL: CRITICAL_SEV_CODE,
    MAJOR: MAJOR_SEV_CODE,
    MINOR: MINOR_SEV_CODE,
    WARNING: WARNING_SEV_CODE,
    INDETERMINATE: INDETER_SEV_CODE,
    CLEARED: CLEARED_SEV_CODE,
    NORMAL: NORMAL_SEV_CODE,
    INFORM: INFORM_SEV_CODE,
    DEBUG: DEBUG_SEV_CODE,
    AUTH: AUTH_SEV_CODE,
    UNKNOWN: UNKNOWN_SEV_CODE,
}

_ABBREV_SEVERITY_MAP = {
    CRITICAL: 'Crit',
    MAJOR: 'Majr',
    MINOR: 'Minr',
    WARNING: 'Warn',
    INDETERMINATE: 'Ind ',
    CLEARED: 'Clrd',
    NORMAL: 'Norm',
    INFORM: 'Info',
    DEBUG: 'Dbug',
    AUTH: 'Sec ',
    UNKNOWN: 'Unkn',
}

_COLOR_MAP = {
    CRITICAL: '\033[91m',
    MAJOR: '\033[95m',
    MINOR: '\033[93m',
    WARNING: '\033[96m',
    INDETERMINATE: '\033[92m',
    CLEARED: '\033[92m',
    NORMAL: '\033[92m',
    INFORM: '\033[92m',
    DEBUG: '\033[90m',
    AUTH: '\033[90m',
    UNKNOWN: '\033[90m',
}

ENDC = '\033[0m'


def is_valid(name):
    return name in _SEVERITY_MAP


def name_to_code(name):
    return _SEVERITY_MAP.get(name.lower(), UNKNOWN_SEV_CODE)


def parse_severity(name):
    if name:
        for severity in _SEVERITY_MAP:
            if name.lower() == severity.lower():
                return severity
    return NOT_VALID


def trend(previous, current):
    if name_to_code(previous) > name_to_code(current):
        return MORE_SEVERE
    elif name_to_code(previous) < name_to_code(current):
        return LESS_SEVERE
    else:
        return NO_CHANGE


def status_from_severity(previous_severity, current_severity, current_status=None):
    if current_severity in [NORMAL, CLEARED]:
        return status_code.CLOSED
    if trend(previous_severity, current_severity) == MORE_SEVERE:
        return status_code.OPEN
    return current_status


