
from alerta.app import severity
from alerta.models import severity_code

"""
Possible alert status codes.
"""

OPEN_STATUS_CODE = 1
ASSIGN_STATUS_CODE = 2
ACK_STATUS_CODE = 3
CLOSED_STATUS_CODE = 4
EXPIRED_STATUS_CODE = 5
BLACKOUT_STATUS_CODE = 6
SHELVED_STATUS_CODE = 7
UNKNOWN_STATUS_CODE = 9

OPEN = 'open'
ASSIGN = 'assign'
ACK = 'ack'
CLOSED = 'closed'
EXPIRED = 'expired'
BLACKOUT = 'blackout'
SHELVED = 'shelved'
UNKNOWN = 'unknown'
NOT_VALID = 'notValid'

ALL = [OPEN, ASSIGN, ACK, CLOSED, EXPIRED, UNKNOWN]

_STATUS_MAP = {
    OPEN: OPEN_STATUS_CODE,
    ASSIGN: ASSIGN_STATUS_CODE,
    ACK: ACK_STATUS_CODE,
    CLOSED: CLOSED_STATUS_CODE,
    EXPIRED: EXPIRED_STATUS_CODE,
    BLACKOUT: BLACKOUT_STATUS_CODE,
    SHELVED: SHELVED_STATUS_CODE,
    UNKNOWN: UNKNOWN_STATUS_CODE,
}


def is_valid(name):
    return name in _STATUS_MAP


def name_to_code(name):
    return _STATUS_MAP.get(name, UNKNOWN_STATUS_CODE)


def parse_status(name):
    if name:
        for st in _STATUS_MAP:
            if name.lower() == st.lower():
                return st
    return NOT_VALID


def status_from_severity(previous_severity, current_severity, previous_status=OPEN, current_status=UNKNOWN):
    if current_severity in [severity_code.NORMAL, severity_code.CLEARED, severity_code.OK]:
        return CLOSED
    if current_status == BLACKOUT:
        return BLACKOUT
    if current_status == SHELVED:
        return SHELVED
    if current_status in [CLOSED, EXPIRED]:
        return OPEN
    if severity.trend(previous_severity, current_severity) == severity_code.MORE_SEVERE:
        return OPEN
    return previous_status
