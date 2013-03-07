import status

"""
Possible alert severity codes.

See ITU-T perceived severity model M.3100 and CCITT Rec X.736
http://tools.ietf.org/html/rfc5674
http://www.itu.int/rec/T-REC-M.3100
http://www.itu.int/rec/T-REC-X.736-199201-I
"""

CRITICAL_SEV_CODE = 1
MAJOR_SEV_CODE = 2
MINOR_SEV_CODE = 3
WARNING_SEV_CODE = 4
NORMAL_SEV_CODE = 5
CLEAR_SEV_CODE = 5
INFORM_SEV_CODE = 6
DEBUG_SEV_CODE = 7
AUTH_SEV_CODE = 8
UNKNOWN_SEV_CODE = 9
INDETER_SEV_CODE = 9

# NOTE: The display text in single quotes can be changed depending on preference.
# eg. CRITICAL = 'critical' or CRITICAL = 'CRITICAL'

CRITICAL = 'critical'
MAJOR = 'major'
MINOR = 'minor'
WARNING = 'warning'
NORMAL = 'normal'
CLEAR = 'clear'
INFORM = 'informational'
DEBUG = 'debug'
AUTH = 'security'
UNKNOWN = 'unknown'
INDETERMINATE = 'indeterminate'

ALL = [CRITICAL, MAJOR, MINOR, WARNING, NORMAL, CLEAR, INFORM, DEBUG, AUTH, UNKNOWN, INDETERMINATE]

_SEVERITY_MAP = {
    CRITICAL: CRITICAL_SEV_CODE,
    MAJOR: MAJOR_SEV_CODE,
    MINOR: MINOR_SEV_CODE,
    WARNING: WARNING_SEV_CODE,
    NORMAL: NORMAL_SEV_CODE,
    CLEAR: CLEAR_SEV_CODE,
    INFORM: INFORM_SEV_CODE,
    DEBUG: DEBUG_SEV_CODE,
    AUTH: AUTH_SEV_CODE,
    UNKNOWN: UNKNOWN_SEV_CODE,
    INDETERMINATE: INDETER_SEV_CODE,
}

_ABBREV_SEVERITY_MAP = {
    CRITICAL: 'Crit',
    MAJOR: 'Majr',
    MINOR: 'Minr',
    WARNING: 'Warn',
    NORMAL: 'Norm',
    CLEAR: 'Clr ',
    INFORM: 'Info',
    DEBUG: 'Dbug',
    AUTH: 'Sec ',
    UNKNOWN: 'Unkn',
    INDETERMINATE: 'Ind ',
}

_COLOR_MAP = {
    CRITICAL: '\033[91m',
    MAJOR: '\033[95m',
    MINOR: '\033[93m',
    WARNING: '\033[96m',
    NORMAL: '\033[92m',
    INFORM: '\033[92m',
    DEBUG: '\033[90m',
}

ENDC = '\033[0m'


def is_valid(name):
    return name in _SEVERITY_MAP


def name_to_code(name):
    return _SEVERITY_MAP.get(name.title(), UNKNOWN_SEV_CODE)


def parse_severity(name):
    if name:
        for sev in _SEVERITY_MAP:
            if name.lower() == sev.lower():
                return sev
    return 'notValid'


def trend(previous, current):

    if name_to_code(previous) > name_to_code(current):
        return 'moreSevere'
    elif name_to_code(previous) < name_to_code(current):
        return 'lessSevere'
    else:
        return 'noChange'


def status_from_severity(previous, current):

    if current == NORMAL:
        return status.CLOSED

    trend_indication = trend(previous, current)
    if trend_indication == 'moreSevere':
        return status.OPEN
    elif trend_indication == 'lessSevere':
        return status.OPEN

