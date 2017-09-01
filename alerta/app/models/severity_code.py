"""
Possible alert severity codes.

See ITU-T perceived severity model M.3100 and CCITT Rec X.736
http://tools.ietf.org/html/rfc5674
http://www.itu.int/rec/T-REC-M.3100
http://www.itu.int/rec/T-REC-X.736-199201-I

Alarm Model State           ITU Perceived Severity      syslog SEVERITY (Name)
      6                     Critical                    1 (Alert)
      5                     Major                       2 (Critical)
      4                     Minor                       3 (Error)
      3                     Warning                     4 (Warning)
      2                     Indeterminate               5 (Notice)
      1                     Cleared                     5 (Notice)
"""

# NOTE: The display text in single quotes can be changed depending on preference.
# eg. CRITICAL = 'critical' or CRITICAL = 'CRITICAL'

AUTH = 'security'
CRITICAL = 'critical'
MAJOR = 'major'
MINOR = 'minor'
WARNING = 'warning'
INDETERMINATE = 'indeterminate'
CLEARED = 'cleared'
NORMAL = 'normal'
OK = 'ok'
INFORM = 'informational'
DEBUG = 'debug'
TRACE = 'trace'
UNKNOWN = 'unknown'
NOT_VALID = 'notValid'

MORE_SEVERE = 'moreSevere'
NO_CHANGE = 'noChange'
LESS_SEVERE = 'lessSevere'

SEVERITY_MAP = {
    'security': 0,
    'critical': 1,
    'major': 2,
    'minor': 3,
    'warning': 4,
    'indeterminate': 5,
    'cleared': 5,
    'normal': 5,
    'ok': 5,
    'informational': 6,
    'debug': 7,
    'trace': 8,
    'unknown': 9
}

_ABBREV_SEVERITY_MAP = {
    AUTH: 'Sec ',
    CRITICAL: 'Crit',
    MAJOR: 'Majr',
    MINOR: 'Minr',
    WARNING: 'Warn',
    INDETERMINATE: 'Ind ',
    CLEARED: 'Clrd',
    NORMAL: 'Norm',
    OK: 'Ok',
    INFORM: 'Info',
    DEBUG: 'Dbug',
    TRACE: 'Trce',
    UNKNOWN: 'Unkn',
}

_COLOR_MAP = {
    AUTH: '\033[94m',
    CRITICAL: '\033[91m',
    MAJOR: '\033[95m',
    MINOR: '\033[93m',
    WARNING: '\033[96m',
    INDETERMINATE: '\033[92m',
    CLEARED: '\033[92m',
    NORMAL: '\033[92m',
    OK: '\033[92m',
    INFORM: '\033[92m',
    DEBUG: '\033[90m',
    TRACE: '\033[97m',
    UNKNOWN: '\033[90m',
}

ENDC = '\033[0m'


class Severity(object):

    SEVERITY_MAP = {
        'security': 0,
        'critical': 1,
        'major': 2,
        'minor': 3,
        'warning': 4,
        'indeterminate': 5,
        'cleared': 5,
        'normal': 5,
        'ok': 5,
        'informational': 6,
        'debug': 7,
        'trace': 8,
        'unknown': 9
    }

    def __init__(self, app=None):
        self.app = None
        if app:
            self.init_app(app)

    def init_app(self, app):
        if 'SEVERITY_MAP' in app.config:
            Severity.SEVERITY_MAP = app.config['SEVERITY_MAP']

    @staticmethod
    def is_valid(name):
        return name in Severity.SEVERITY_MAP

    @staticmethod
    def name_to_code(name):
        return Severity.SEVERITY_MAP.get(name, Severity.SEVERITY_MAP.get(UNKNOWN))

    @staticmethod
    def parse_severity(name):
        if name:
            for severity in Severity.SEVERITY_MAP:
                if name.lower() == severity.lower():
                    return severity
        return NOT_VALID

    def trend(self, previous, current):
        if self.name_to_code(previous) > self.name_to_code(current):
            return MORE_SEVERE
        elif self.name_to_code(previous) < self.name_to_code(current):
            return LESS_SEVERE
        else:
            return NO_CHANGE
