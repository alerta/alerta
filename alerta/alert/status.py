""" Possible alert severity codes.

See ITU-T perceived severity model M.3100 and CCITT Rec X.736
http://tools.ietf.org/html/rfc5674
http://www.itu.int/rec/T-REC-M.3100
http://www.itu.int/rec/T-REC-X.736-199201-I
"""

OPEN_STATUS_CODE = 1
ACK_STATUS_CODE = 2
CLOSED_STATUS_CODE = 3
EXPIRED_STATUS_CODE = 4
UNKNOWN_STATUS_CODE = 9

OPEN = 'Open'
ACK = 'Acknowledged'
CLOSED = 'Closed'
EXPIRED = 'Expired'
UNKNOWN = 'Unknown'

ALL = [OPEN, ACK, CLOSED, EXPIRED, UNKNOWN]

_STATUS_MAP = {
    OPEN: OPEN_STATUS_CODE,
    ACK: ACK_STATUS_CODE,
    CLOSED: CLOSED_STATUS_CODE,
    EXPIRED: EXPIRED_STATUS_CODE,
}


def name_to_code(name):
    return _STATUS_MAP.get(name, UNKNOWN_STATUS_CODE)
