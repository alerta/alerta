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
from enum import Enum

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


class Severity(str, Enum):
    SECURITY = 'security'
    CRITICAL = 'critical'
    MAJOR = 'major'
    MINOR = 'minor'
    WARNING = 'warning'
    INFORMATIONAL = 'informational'
    DEBUG = 'debug'
    TRACE = 'trace'
    INDETERMINATE = 'indeterminate'
    NORMAL = 'normal'
    CLEARED = 'cleared'
    OK = 'ok'
    UNKNOWN = 'unknown'

    @staticmethod
    def from_str(s):
        if s:
            return Severity[s.upper()]

    def code(self):
        return -SEVERITY_MAP[self.value]

    @staticmethod
    def trend(previous, current):
        if previous.code() < current.code():
            return Trend.MORE_SEVERE
        elif previous.code() > current.code():
            return Trend.LESS_SEVERE
        else:
            return Trend.NO_CHANGE


NOT_OK = [
    Severity.SECURITY,
    Severity.CRITICAL,
    Severity.MAJOR,
    Severity.MINOR,
    Severity.WARNING,
    Severity.DEBUG,
    Severity.TRACE
]
ALL_OK = [
    Severity.NORMAL,
    Severity.CLEARED,
    Severity.OK,
]


class Trend(str, Enum):
    MORE_SEVERE = 'moreSevere'
    NO_CHANGE = 'noChange'
    LESS_SEVERE = 'lessSevere'

    @staticmethod
    def from_str(t):
        if t:
            return Trend(t)
