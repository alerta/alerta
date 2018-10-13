"""
Alarm states and transition paths.

See ANSI/ISA 18.2 Management of Alarm Systems for the Process Industries
https://www.isa.org/store/ansi/isa-182-2016/46962105

"""

# FIXME - probably need to automatically ACK RTN_UNACK alerts based on timeout

from alerta.models.alarms import AlarmModel

SEVERITY_MAP = {
    'Critical': 5,
    'High': 4,
    'Medium': 3,
    'Low': 2,
    'Advisory': 1,
    'OK': 0
}
DEFAULT_NORMAL_SEVERITY = 'OK'
DEFAULT_PREVIOUS_SEVERITY = 'OK'

COLOR_MAP = {
    'severity': {
        'Critical': 'red',
        'High': 'orange',
        'Medium': 'yellow',
        'Low': 'dodgerblue',
        'Advisory': 'lightblue',
        'OK': '#00CC00',  # lime green
        'unknown': 'silver'
    },
    'text': 'black',
    'highlight': 'skyblue '
}

NORMAL = 'Normal'
UNACK = 'Unack'
ACK = 'Ack'
RTN_UNACK = 'RTN Unack'
LATCHED_UNACK = 'Latch Unack'
LATCHED_ACK = 'Latch Ack'
SHELVED = 'Shelved'
SUPPRESSED_BY_DESIGN = 'Supp. by Design'  # not used
OUT_OF_SERVICE = 'Out-of-Service'

ACTIVE = [
    UNACK,
    ACK,
    RTN_UNACK,
    LATCHED_UNACK,
    LATCHED_ACK
]
INACTIVE = [
    NORMAL,
    SHELVED,
    SUPPRESSED_BY_DESIGN,
    OUT_OF_SERVICE
]

MORE_SEVERE = 'moreSevere'
NO_CHANGE = 'noChange'
LESS_SEVERE = 'lessSevere'

ACTION_ACK = 'ack'
ACTION_RESET = 'reset'
ACTION_UNACK = 'unack'
ACTION_SHELVE = 'shelve'
ACTION_UNSHELVE = 'unshelve'
ACTION_CLOSE = 'close'

# TODO: only enable actions if it's possible to transition


class StateMachine(AlarmModel):

    def register(self, app):
        self.name = 'ANSI/ISA 18.2'

        StateMachine.Severity = app.config['SEVERITY_MAP'] or SEVERITY_MAP
        StateMachine.Colors = app.config['COLOR_MAP'] or COLOR_MAP

        StateMachine.DEFAULT_STATUS = NORMAL
        StateMachine.DEFAULT_NORMAL_SEVERITY = app.config['DEFAULT_NORMAL_SEVERITY'] or DEFAULT_NORMAL_SEVERITY
        StateMachine.DEFAULT_PREVIOUS_SEVERITY = app.config['DEFAULT_PREVIOUS_SEVERITY'] or DEFAULT_PREVIOUS_SEVERITY

    def trend(self, previous, current):
        if StateMachine.Severity[previous] < StateMachine.Severity[current]:
            return MORE_SEVERE
        elif StateMachine.Severity[previous] > StateMachine.Severity[current]:
            return LESS_SEVERE
        else:
            return NO_CHANGE

    def transition(self, previous_severity, current_severity, previous_status=None, current_status=None, action=None, **kwargs):

        state = previous_status or StateMachine.DEFAULT_STATUS
        latched = kwargs.get('is_latched', False)

        # Alarm Occurs, Normal (A) -> Unack (B)
        if state == NORMAL:
            if current_severity != 'OK':
                return current_severity, UNACK
        # Operator Ack, Unack (B) -> Ack (C)
        if state == UNACK:
            if action == ACTION_ACK:
                return current_severity, ACK
        # Re-Alarm, Ack (C) -> Unack (B)
        if state == ACK:
            if self.trend(previous_severity, current_severity) == MORE_SEVERE:
                return current_severity, UNACK
        # Process RTN Alarm Clears, Ack (C) -> Normal (A)
        if state == ACK and not latched:
            if current_severity == 'OK':
                return current_severity, NORMAL
        # Process RTN Latched Alarm, Ack (C) -> Latch Ack (F)
        if state == ACK and latched:
            if current_severity == 'OK':
                return current_severity, LATCHED_ACK
        # Process RTN and Alarm Clears, Unack (B) -> RTN Unack (D)
        if state == UNACK and not latched:
            if current_severity == 'OK':
                return current_severity, RTN_UNACK
        # Process RTN, Unack (B) -> Latch Unack (E)
        if state == UNACK and latched:
            if current_severity == 'OK':
                return current_severity, LATCHED_UNACK
        # Operator Ack, RTN Unack (D) -> Normal (A)
        if state == RTN_UNACK:
            if action == ACTION_ACK:
                return current_severity, NORMAL
        # Re-Alarm Unack, RTN Unack (D) -> Unack (B)  # XXX - missing from descriptions?
        if state == RTN_UNACK:
            if current_severity != 'OK':
                return current_severity, UNACK
        # Operator Resets, Latch Unack (E) -> RTN Unack (D)
        if state == LATCHED_UNACK:
            if action == ACTION_RESET:
                return current_severity, RTN_UNACK
        # Operator Ack, Latch Unack (E) -> Latch Ack (F)
        if state == LATCHED_UNACK:
            if action == ACTION_ACK:
                return current_severity, LATCHED_ACK
        # Operator Resets, Latch Ack (F) -> Normal (A)
        if state == LATCHED_ACK:
            if action == ACTION_RESET:
                return current_severity, NORMAL
        # Shelve (Any->G)
        if action == ACTION_SHELVE:
            return current_severity, SHELVED
        # Unshelve (G->Any)
        if action == ACTION_UNSHELVE:
            return current_severity, UNACK
        # Designed Suppression (Any->H)

        # Designed Unsuppression (H->Any)

        # Remove-from-Service (Any->I)

        # Return-to-Service (I->Any)

        return current_severity, state

    @staticmethod
    def is_suppressed(alert):
        return alert.status in [SUPPRESSED_BY_DESIGN, OUT_OF_SERVICE]
