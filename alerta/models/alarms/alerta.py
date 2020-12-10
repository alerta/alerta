from flask import current_app

from alerta.exceptions import ApiError, InvalidAction
from alerta.models.alarms import AlarmModel
from alerta.models.enums import Action, Severity, Status, TrendIndication

SEVERITY_MAP = {
    Severity.Security: 0,
    Severity.Critical: 1,
    Severity.Major: 2,
    Severity.Minor: 3,
    Severity.Warning: 4,
    Severity.Indeterminate: 5,
    Severity.Informational: 6,
    Severity.Normal: 7,
    Severity.Ok: 7,
    Severity.Cleared: 7,
    Severity.Debug: 8,
    Severity.Trace: 9,
    Severity.Unknown: 10
}
DEFAULT_NORMAL_SEVERITY = Severity.Normal  # 'normal', 'ok', 'cleared'
DEFAULT_PREVIOUS_SEVERITY = Severity.Indeterminate


COLOR_MAP = {
    'severity': {
        Severity.Security: 'blue',
        Severity.Critical: 'red',
        Severity.Major: 'orange',
        Severity.Minor: 'yellow',
        Severity.Warning: 'dodgerblue',
        Severity.Indeterminate: 'lightblue',
        Severity.Cleared: '#00CC00',  # lime green
        Severity.Normal: '#00CC00',
        Severity.Ok: '#00CC00',
        Severity.Informational: '#00CC00',
        Severity.Debug: '#9D006D',  # purple
        Severity.Trace: '#7554BF',  # violet
        Severity.Unknown: 'silver'
    },
    'status': {
        Status.Ack: 'skyblue',
        Status.Shelved: 'skyblue'
    },
    'text': 'black'
}

STATUS_MAP = {
    Status.Open: 'A',
    Status.Assign: 'B',
    Status.Ack: 'C',
    Status.Shelved: 'D',
    Status.Blackout: 'E',
    Status.Closed: 'F',
    Status.Expired: 'G',
    Status.Unknown: 'H'
}


ACTION_ALL = [
    Action.OPEN,
    Action.ASSIGN,
    Action.ACK,
    Action.UNACK,
    Action.SHELVE,
    Action.UNSHELVE,
    Action.CLOSE,
    Action.EXPIRED,
    Action.TIMEOUT
]


class StateMachine(AlarmModel):

    @property
    def valid_severities(self):
        return sorted(StateMachine.Severity, key=StateMachine.Severity.get)

    def register(self, app):
        from alerta.management.views import __version__
        self.name = 'Alerta %s' % __version__

        StateMachine.Severity = app.config['SEVERITY_MAP'] or SEVERITY_MAP
        StateMachine.Colors = app.config['COLOR_MAP'] or COLOR_MAP
        StateMachine.Status = STATUS_MAP

        StateMachine.DEFAULT_STATUS = Status.Open
        StateMachine.DEFAULT_NORMAL_SEVERITY = app.config['DEFAULT_NORMAL_SEVERITY'] or DEFAULT_NORMAL_SEVERITY
        StateMachine.DEFAULT_PREVIOUS_SEVERITY = app.config['DEFAULT_PREVIOUS_SEVERITY'] or DEFAULT_PREVIOUS_SEVERITY

        if StateMachine.DEFAULT_NORMAL_SEVERITY not in StateMachine.Severity:
            raise RuntimeError('DEFAULT_NORMAL_SEVERITY ({}) is not one of {}'.format(
                StateMachine.DEFAULT_NORMAL_SEVERITY, ', '.join(self.valid_severities)))
        if StateMachine.DEFAULT_PREVIOUS_SEVERITY not in StateMachine.Severity:
            raise RuntimeError('DEFAULT_PREVIOUS_SEVERITY ({}) is not one of {}'.format(
                StateMachine.DEFAULT_PREVIOUS_SEVERITY, ', '.join(self.valid_severities)))

        StateMachine.NORMAL_SEVERITY_LEVEL = StateMachine.Severity[StateMachine.DEFAULT_NORMAL_SEVERITY]

    def trend(self, previous, current):
        if previous not in StateMachine.Severity or current not in StateMachine.Severity:
            return TrendIndication.No_Change

        if StateMachine.Severity[previous] > StateMachine.Severity[current]:
            return TrendIndication.More_Severe
        elif StateMachine.Severity[previous] < StateMachine.Severity[current]:
            return TrendIndication.Less_Severe
        else:
            return TrendIndication.No_Change

    def transition(self, alert, current_status=None, previous_status=None, action=None, **kwargs):
        current_status = current_status or StateMachine.DEFAULT_STATUS
        previous_status = previous_status or StateMachine.DEFAULT_STATUS

        current_severity = alert.severity
        previous_severity = alert.previous_severity or StateMachine.DEFAULT_PREVIOUS_SEVERITY

        valid_severities = sorted(StateMachine.Severity, key=StateMachine.Severity.get)
        if current_severity not in StateMachine.Severity:
            raise ApiError('Severity ({}) is not one of {}'.format(current_severity, ', '.join(valid_severities)), 400)

        def next_state(rule, severity, status):
            current_app.logger.info(
                'State Transition: Rule #{} STATE={:8s} ACTION={:8s} SET={:8s} '
                'SEVERITY={:13s}-> {:8s} HISTORY={:8s}-> {:8s} => SEVERITY={:8s}, STATUS={:8s}'.format(
                    rule,
                    current_status,
                    action or '',
                    alert.status,
                    previous_severity,
                    current_severity,
                    previous_status,
                    current_status,
                    severity,
                    status
                ))
            return severity, status

        # if an unrecognised action is passed then assume state transition has been handled
        # by a take_action() plugin and return the current severity and status unchanged
        if action and action not in ACTION_ALL:
            return next_state('ACT-1', current_severity, alert.status)

        # if alert has non-default status then assume state transition has been handled
        # by a pre_receive() plugin and return the current severity and status, accounting
        # for auto-closing normal alerts, otherwise unchanged
        if not action and alert.status != StateMachine.DEFAULT_STATUS:
            if StateMachine.Severity[current_severity] == StateMachine.NORMAL_SEVERITY_LEVEL:
                return next_state('SET-1', StateMachine.DEFAULT_NORMAL_SEVERITY, Status.Closed)
            return next_state('SET-*', current_severity, alert.status)

        # state transition determined by operator action, if any, or severity changes
        state = current_status

        if action == Action.UNACK:
            if state == Status.Ack:
                return next_state('UNACK-1', current_severity, previous_status)
            else:
                raise InvalidAction('invalid action for current {} status'.format(state))

        if action == Action.UNSHELVE:
            if state == Status.Shelved:
                # as per ISA 18.2 recommendation 11.7.3 manually unshelved alarms transition to previous status
                return next_state('UNSHL-1', current_severity, previous_status)
            else:
                raise InvalidAction('invalid action for current {} status'.format(state))

        if action == Action.EXPIRED:
            return next_state('EXP-0', current_severity, Status.Expired)

        if action == Action.TIMEOUT:
            if previous_status == Status.Ack:
                return next_state('ACK-0', current_severity, Status.Ack)
            else:
                return next_state('OPEN-0', current_severity, Status.Open)

        if state == Status.Open:
            if action == Action.OPEN:
                raise InvalidAction('alert is already in {} status'.format(state))
            if action == Action.ACK:
                return next_state('OPEN-1', current_severity, Status.Ack)
            if action == Action.SHELVE:
                return next_state('OPEN-2', current_severity, Status.Shelved)
            if action == Action.CLOSE:
                return next_state('OPEN-3', StateMachine.DEFAULT_NORMAL_SEVERITY, Status.Closed)

        if state == Status.Assign:
            pass

        if state == Status.Ack:
            if action == Action.OPEN:
                return next_state('ACK-1', current_severity, Status.Open)
            if action == Action.ACK:
                raise InvalidAction('alert is already in {} status'.format(state))
            if action == Action.SHELVE:
                return next_state('ACK-2', current_severity, Status.Shelved)
            if action == Action.CLOSE:
                return next_state('ACK-3', StateMachine.DEFAULT_NORMAL_SEVERITY, Status.Closed)

            # re-open ack'ed alerts if the severity actually increases
            # not just because the previous severity is the default
            if previous_severity != StateMachine.DEFAULT_PREVIOUS_SEVERITY:
                if self.trend(previous_severity, current_severity) == TrendIndication.More_Severe:
                    return next_state('ACK-4', current_severity, Status.Open)

        if state == Status.Shelved:
            if action == Action.OPEN:
                return next_state('SHL-1', current_severity, Status.Open)
            if action == Action.ACK:
                raise InvalidAction('invalid action for current {} status'.format(state))
            if action == Action.SHELVE:
                raise InvalidAction('alert is already in {} status'.format(state))
            if action == Action.CLOSE:
                return next_state('SHL-2', StateMachine.DEFAULT_NORMAL_SEVERITY, Status.Closed)

        if state == Status.Blackout:
            if action == Action.CLOSE:
                return next_state('BLK-1', StateMachine.DEFAULT_NORMAL_SEVERITY, Status.Closed)

            if previous_status != Status.Blackout:
                return next_state('BLK-2', current_severity, previous_status)
            else:
                return next_state('BLK-*', current_severity, alert.status)

        if state == Status.Closed:
            if action == Action.OPEN:
                return next_state('CLS-1', previous_severity, Status.Open)
            if action == Action.ACK:
                raise InvalidAction('invalid action for current {} status'.format(state))
            if action == Action.SHELVE:
                raise InvalidAction('invalid action for current {} status'.format(state))
            if action == Action.CLOSE:
                raise InvalidAction('alert is already in {} status'.format(state))

            if StateMachine.Severity[current_severity] != StateMachine.NORMAL_SEVERITY_LEVEL:
                if previous_status == Status.Shelved:
                    return next_state('CLS-2', previous_severity, Status.Shelved)
                else:
                    return next_state('CLS-3', previous_severity, Status.Open)

        # auto-close normal severity alerts from ANY state
        if StateMachine.Severity[current_severity] == StateMachine.NORMAL_SEVERITY_LEVEL:
            return next_state('CLS-*', StateMachine.DEFAULT_NORMAL_SEVERITY, Status.Closed)

        if state == Status.Expired:
            if action and action != Action.OPEN:
                raise InvalidAction('invalid action for current {} status'.format(state))
            if StateMachine.Severity[current_severity] != StateMachine.NORMAL_SEVERITY_LEVEL:
                return next_state('EXP-1', current_severity, Status.Open)

        return next_state('ALL-*', current_severity, current_status)

    @staticmethod
    def is_suppressed(alert):
        return alert.status == Status.Blackout
