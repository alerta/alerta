
from alerta.common import severity_code

SYSLOG_FACILITY_NAMES = [
    "kern",
    "user",
    "mail",
    "daemon",
    "auth",
    "syslog",
    "lpr",
    "news",
    "uucp",
    "cron",
    "authpriv",
    "ftp",
    "ntp",
    "audit",
    "alert",
    "clock",
    "local0",
    "local1",
    "local2",
    "local3",
    "local4",
    "local5",
    "local6",
    "local7"
]

SYSLOG_SEVERITY_NAMES = [
    "emerg",
    "alert",
    "crit",
    "err",
    "warning",
    "notice",
    "info",
    "debug"
]

_SYSLOG_SEVERITY_MAP = {
    'emerg':   severity_code.CRITICAL,
    'alert':   severity_code.CRITICAL,
    'crit':    severity_code.MAJOR,
    'err':     severity_code.MINOR,
    'warning': severity_code.WARNING,
    'notice':  severity_code.NORMAL,
    'info':    severity_code.INFORM,
    'debug':   severity_code.DEBUG,
    }

DEFAULT_UDP_PORT = 514
DEFAULT_TCP_PORT = 514


def priority_to_code(name):
    return _SYSLOG_SEVERITY_MAP.get(name, severity_code.UNKNOWN_SEV_CODE)


def decode_priority(priority):
    facility = priority >> 3
    facility = SYSLOG_FACILITY_NAMES[facility]
    level = priority & 7
    level = SYSLOG_SEVERITY_NAMES[level]
    return facility, level