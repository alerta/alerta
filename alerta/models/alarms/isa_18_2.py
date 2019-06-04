"""
Alarm states and transition paths.

See ANSI/ISA 18.2 Management of Alarm Systems for the Process Industries
https://www.isa.org/store/ansi/isa-182-2016/46962105

"""


from flask import current_app

from alerta.models.alarms import AlarmModel

CRITICAL = 'Critical'
HIGH = 'High'
MEDIUM = 'Medium'
LOW = 'Low'
ADVISORY = 'Advisory'
OK = 'OK'
UNKNOWN = 'Unknown'

SEVERITY_MAP = {
    CRITICAL: 5,
    HIGH: 4,
    MEDIUM: 3,
    LOW: 2,
    ADVISORY: 1,
    OK: 0
}
DEFAULT_NORMAL_SEVERITY = OK
DEFAULT_PREVIOUS_SEVERITY = OK

COLOR_MAP = {
    'severity': {
        CRITICAL: 'red',
        HIGH: 'orange',
        MEDIUM: 'yellow',
        LOW: 'dodgerblue',
        ADVISORY: 'lightblue',
        OK: '#00CC00',  # lime green
        UNKNOWN: 'silver'
    },
    'text': 'black'
}

A_NORM = 'NORM'
B_UNACK = 'UNACK'
C_ACKED = 'ACKED'
D_RTNUN = 'RTNUN'
E_SHLVD = 'SHLVD'
F_DSUPR = 'DSUPR'
G_OOSRV = 'OOSRV'

STATUS_MAP = {
    A_NORM: 'A',
    B_UNACK: 'B',
    C_ACKED: 'C',
    D_RTNUN: 'D',
    E_SHLVD: 'E',
    F_DSUPR: 'F',
    G_OOSRV: 'G'
}

MORE_SEVERE = 'moreSevere'
NO_CHANGE = 'noChange'
LESS_SEVERE = 'lessSevere'

ACTION_ACK = 'ack'
ACTION_SHELVE = 'shelve'
ACTION_UNSHELVE = 'unshelve'


class StateMachine(AlarmModel):

    def register(self, app):
        self.name = 'ANSI/ISA 18.2'

        StateMachine.Severity = app.config['SEVERITY_MAP'] or SEVERITY_MAP
        StateMachine.Colors = app.config['COLOR_MAP'] or COLOR_MAP
        StateMachine.Status = STATUS_MAP

        StateMachine.DEFAULT_STATUS = A_NORM
        StateMachine.DEFAULT_NORMAL_SEVERITY = app.config['DEFAULT_NORMAL_SEVERITY'] or DEFAULT_NORMAL_SEVERITY
        StateMachine.DEFAULT_PREVIOUS_SEVERITY = app.config['DEFAULT_PREVIOUS_SEVERITY'] or DEFAULT_PREVIOUS_SEVERITY

    def trend(self, previous, current):
        valid_severities = sorted(StateMachine.Severity, key=StateMachine.Severity.get)
        assert previous in StateMachine.Severity, 'Severity is not one of %s' % ', '.join(valid_severities)
        assert current in StateMachine.Severity, 'Severity is not one of %s' % ', '.join(valid_severities)

        if StateMachine.Severity[previous] < StateMachine.Severity[current]:
            return MORE_SEVERE
        elif StateMachine.Severity[previous] > StateMachine.Severity[current]:
            return LESS_SEVERE
        else:
            return NO_CHANGE

    def transition(self, alert, current_status=None, previous_status=None, action=None, **kwargs):
        state = current_status or StateMachine.DEFAULT_STATUS

        current_severity = alert.severity
        previous_severity = alert.previous_severity or StateMachine.DEFAULT_PREVIOUS_SEVERITY

        def next_state(rule, severity, status):
            current_app.logger.info(
                'State Transition: Rule {}: STATE={} => SEVERITY={}, STATUS={}'.format(
                    rule,
                    state,
                    severity,
                    status
                )
            )
            return severity, status

        # if alert has non-default status then assume state transition has been handled
        # by a pre_receive() plugin and return the current severity and status
        if not action and alert.status != StateMachine.DEFAULT_STATUS:
            return next_state('External State Change, Any (*) -> Any (*)', current_severity, alert.status)

        # Operator Shelve, Any (*) -> Shelve (E)
        if action == ACTION_SHELVE:
            return next_state('Operator Shelve, Any (*) -> Shelve (E)', current_severity, E_SHLVD)
        # Operator Unshelve, Shelve (E) -> Normal (A) or Unack (B)
        if action == ACTION_UNSHELVE:
            if current_severity == StateMachine.DEFAULT_NORMAL_SEVERITY:
                return next_state('Operator Unshelve, Shelve (E) -> Normal (A)', current_severity, A_NORM)
            else:
                return next_state('Operator Unshelve, Shelve (E) -> Unack (B)', current_severity, B_UNACK)

        # Alarm Occurs, Normal (A) -> Unack (B)
        if state == A_NORM:
            if current_severity != StateMachine.DEFAULT_NORMAL_SEVERITY:
                return next_state('Alarm Occurs, Normal (A) -> Unack (B)', current_severity, B_UNACK)
        # Operator Ack, Unack (B) -> Ack (C)
        if state == B_UNACK:
            if action == ACTION_ACK:
                return next_state('Operator Ack, Unack (B) -> Ack (C)', current_severity, C_ACKED)
        # Re-Alarm, Ack (C) -> Unack (B)
        if state == C_ACKED:
            if self.trend(previous_severity, current_severity) == MORE_SEVERE:
                if previous_severity != StateMachine.DEFAULT_PREVIOUS_SEVERITY:
                    return next_state('Re-Alarm, Ack (C) -> Unack (B)', current_severity, B_UNACK)
        # Process RTN Alarm Clears, Ack (C) -> Normal (A)
        if state == C_ACKED:
            if current_severity == StateMachine.DEFAULT_NORMAL_SEVERITY:
                return next_state('Process RTN Alarm Clears, Ack (C) -> Normal (A)', current_severity, A_NORM)
        # Process RTN and Alarm Clears, Unack (B) -> RTN Unack (D)
        if state == B_UNACK:
            if current_severity == StateMachine.DEFAULT_NORMAL_SEVERITY:
                return next_state('Process RTN and Alarm Clears, Unack (B) -> RTN Unack (D)', current_severity, D_RTNUN)
        # Operator Ack, RTN Unack (D) -> Normal (A)
        if state == D_RTNUN:
            if action == ACTION_ACK:
                return next_state(' Operator Ack, RTN Unack (D) -> Normal (A)', current_severity, A_NORM)
        # Re-Alarm Unack, RTN Unack (D) -> Unack (B)
        if state == D_RTNUN:
            if current_severity != StateMachine.DEFAULT_NORMAL_SEVERITY:
                return next_state('Re-Alarm Unack, RTN Unack (D) -> Unack (B)', current_severity, B_UNACK)

        # Return from Suppressed-by-design (F) -> Normal (A) or Unack (B)
        if state == F_DSUPR:
            if current_severity == StateMachine.DEFAULT_NORMAL_SEVERITY:
                return next_state('Return from Suppressed-by-design, Suppressed-by-design (G) -> Normal (A)', current_severity, A_NORM)
            else:
                return next_state('Return from Suppressed-by-design, Suppressed-by-design (G) -> Unack (B)', current_severity, B_UNACK)

        # Return from Out-of-service (G) -> Normal (A) or Unack (B)
        if state == G_OOSRV:
            if current_severity == StateMachine.DEFAULT_NORMAL_SEVERITY:
                return next_state('Return from Out-of-service, Out-of-service (G) -> Normal (A)', current_severity, A_NORM)
            else:
                return next_state('Return from Out-of-service, Out-of-service (G) -> Unack (B)', current_severity, B_UNACK)

        return next_state('NOOP', current_severity, current_status)

    @staticmethod
    def is_suppressed(alert):
        return alert.status in [F_DSUPR, G_OOSRV]
