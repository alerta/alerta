from alerta.alert import severity

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
    'emerg':   severity.CRITICAL,
    'alert':   severity.CRITICAL,
    'crit':    severity.MAJOR,
    'err':     severity.MINOR,
    'warning': severity.WARNING,
    'notice':  severity.NORMAL,
    'info':    severity.INFORM,
    'debug':   severity.DEBUG,
    }

DEFAULT_UDP_PORT = 514
DEFAULT_TCP_PORT = 514

def priority_to_code(name):
    return _SYSLOG_SEVERITY_MAP.get(name, severity.UNKNOWN_SEV_CODE)