from enum import Enum


class Status(str, Enum):
    OPEN = 'open'
    ASSIGN = 'assign'
    ACK = 'ack'
    CLOSED = 'closed'
    EXPIRED = 'expired'
    BLACKOUT = 'blackout'
    SHELVED = 'shelved'
    UNKNOWN = 'unknown'

    @staticmethod
    def from_str(s):
        if s:
            return Status(s.lower())


class State(str, Enum):
    NORMAL = 'Normal'
    UNACK = 'Unack'
    ACK = 'Ack'
    RTN_UNACK = 'RTN Unack'
    LATCHED_UNACK = 'Latch Unack'
    LATCHED_ACK = 'Latch Ack'
    SHELVED = 'Shelved'
    SUPPRESSED_BY_DESIGN = 'Supp. by Design'  # not used
    OUT_OF_SERVICE = 'Out-of-Service'


class Action(str, Enum):
    ACTION_ACK = 'ack'
    ACTION_RESET = 'reset'
    ACTION_UNACK = 'unack'
    ACTION_SHELVE = 'shelve'
    ACTION_UNSHELVE = 'unshelve'
    ACTION_CLOSE = 'close'


class HistoryType(str, Enum):
    SEVERITY_CHANGE = 'severity'
    STATUS_CHANGE = 'status'
    ACTION_CHANGE = 'action'
    VALUE_CHANGE = 'value'
