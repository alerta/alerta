from flask import current_app

from alerta.exceptions import ApiError, InvalidAction
from alerta.models.alarms import AlarmModel

SEVERITY_MAP = {
    'security': 0,
    'critical': 1,
    'major': 2,
    'minor': 3,
    'warning': 4,
    'indeterminate': 5,
    'informational': 6,
    'normal': 7,
    'ok': 7,
    'cleared': 7,
    'debug': 8,
    'trace': 9,
    'unknown': 10
}
DEFAULT_NORMAL_SEVERITY = 'normal'  # 'normal', 'ok', 'cleared'
DEFAULT_PREVIOUS_SEVERITY = 'indeterminate'

COLOR_MAP = {
    'severity': {
        'security': 'blue',
        'critical': 'red',
        'major': 'orange',
        'minor': 'yellow',
        'warning': 'dodgerblue',
        'indeterminate': 'lightblue',
        'cleared': '#00CC00',  # lime green
        'normal': '#00CC00',
        'ok': '#00CC00',
        'informational': '#00CC00',
        'debug': '#9D006D',  # purple
        'trace': '#7554BF',  # violet
        'unknown': 'silver'
    },
    'text': 'black'
}

OPEN = 'open'
ASSIGN = 'assign'
ACK = 'ack'
SHELVED = 'shelved'
BLACKOUT = 'blackout'
CLOSED = 'closed'
EXPIRED = 'expired'
UNKNOWN = 'unknown'
NOT_VALID = 'notValid'

STATUS_MAP = {
    OPEN: 'A',
    ASSIGN: 'B',
    ACK: 'C',
    SHELVED: 'D',
    BLACKOUT: 'E',
    CLOSED: 'F',
    EXPIRED: 'G',
    UNKNOWN: 'H'
}

MORE_SEVERE = 'moreSevere'
NO_CHANGE = 'noChange'
LESS_SEVERE = 'lessSevere'

ACTION_OPEN = 'open'
ACTION_ASSIGN = 'assign'
ACTION_ACK = 'ack'
ACTION_UNACK = 'unack'
ACTION_SHELVE = 'shelve'
ACTION_UNSHELVE = 'unshelve'
ACTION_CLOSE = 'close'
ACTION_EXPIRED = 'expired'
ACTION_TIMEOUT = 'timeout'

ACTION_ALL = [
    ACTION_OPEN,
    ACTION_ASSIGN,
    ACTION_ACK,
    ACTION_UNACK,
    ACTION_SHELVE,
    ACTION_UNSHELVE,
    ACTION_CLOSE,
    ACTION_EXPIRED,
    ACTION_TIMEOUT
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

        StateMachine.DEFAULT_STATUS = OPEN
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
            return NO_CHANGE

        if StateMachine.Severity[previous] > StateMachine.Severity[current]:
            return MORE_SEVERE
        elif StateMachine.Severity[previous] < StateMachine.Severity[current]:
            return LESS_SEVERE
        else:
            return NO_CHANGE

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
                return next_state('SET-1', StateMachine.DEFAULT_NORMAL_SEVERITY, CLOSED)
            return next_state('SET-*', current_severity, alert.status)

        # state transition determined by operator action, if any, or severity changes
        state = current_status

        if action == ACTION_UNACK:
            if state == ACK:
                return next_state('UNACK-1', current_severity, previous_status)
            else:
                raise InvalidAction('invalid action for current {} status'.format(state))

        if action == ACTION_UNSHELVE:
            if state == SHELVED:
                # as per ISA 18.2 recommendation 11.7.3 manually unshelved alarms transition to previous status
                return next_state('UNSHL-1', current_severity, previous_status)
            else:
                raise InvalidAction('invalid action for current {} status'.format(state))

        if action == ACTION_EXPIRED:
            return next_state('EXP-0', current_severity, EXPIRED)

        if action == ACTION_TIMEOUT:
            if previous_status == ACK:
                return next_state('ACK-0', current_severity, ACK)
            else:
                return next_state('OPEN-0', current_severity, OPEN)

        if state == OPEN:
            if action == ACTION_OPEN:
                raise InvalidAction('alert is already in {} status'.format(state))
            if action == ACTION_ACK:
                return next_state('OPEN-1', current_severity, ACK)
            if action == ACTION_SHELVE:
                return next_state('OPEN-2', current_severity, SHELVED)
            if action == ACTION_CLOSE:
                return next_state('OPEN-3', StateMachine.DEFAULT_NORMAL_SEVERITY, CLOSED)

        if state == ASSIGN:
            pass

        if state == ACK:
            if action == ACTION_OPEN:
                return next_state('ACK-1', current_severity, OPEN)
            if action == ACTION_ACK:
                raise InvalidAction('alert is already in {} status'.format(state))
            if action == ACTION_SHELVE:
                return next_state('ACK-2', current_severity, SHELVED)
            if action == ACTION_CLOSE:
                return next_state('ACK-3', StateMachine.DEFAULT_NORMAL_SEVERITY, CLOSED)

            # re-open ack'ed alerts if the severity actually increases
            # not just because the previous severity is the default
            if previous_severity != StateMachine.DEFAULT_PREVIOUS_SEVERITY:
                if self.trend(previous_severity, current_severity) == MORE_SEVERE:
                    return next_state('ACK-4', current_severity, OPEN)

        if state == SHELVED:
            if action == ACTION_OPEN:
                return next_state('SHL-1', current_severity, OPEN)
            if action == ACTION_ACK:
                raise InvalidAction('invalid action for current {} status'.format(state))
            if action == ACTION_SHELVE:
                raise InvalidAction('alert is already in {} status'.format(state))
            if action == ACTION_CLOSE:
                return next_state('SHL-2', StateMachine.DEFAULT_NORMAL_SEVERITY, CLOSED)

        if state == BLACKOUT:
            if action == ACTION_CLOSE:
                return next_state('BLK-1', StateMachine.DEFAULT_NORMAL_SEVERITY, CLOSED)

            if previous_status != BLACKOUT:
                return next_state('BLK-2', current_severity, previous_status)
            else:
                return next_state('BLK-*', current_severity, alert.status)

        if state == CLOSED:
            if action == ACTION_OPEN:
                return next_state('CLS-1', previous_severity, OPEN)
            if action == ACTION_ACK:
                raise InvalidAction('invalid action for current {} status'.format(state))
            if action == ACTION_SHELVE:
                raise InvalidAction('invalid action for current {} status'.format(state))
            if action == ACTION_CLOSE:
                raise InvalidAction('alert is already in {} status'.format(state))

            if StateMachine.Severity[current_severity] != StateMachine.NORMAL_SEVERITY_LEVEL:
                if previous_status == SHELVED:
                    return next_state('CLS-2', previous_severity, SHELVED)
                else:
                    return next_state('CLS-3', previous_severity, OPEN)

        # auto-close normal severity alerts from ANY state
        if StateMachine.Severity[current_severity] == StateMachine.NORMAL_SEVERITY_LEVEL:
            return next_state('CLS-*', StateMachine.DEFAULT_NORMAL_SEVERITY, CLOSED)

        if state == EXPIRED:
            if action and action != ACTION_OPEN:
                raise InvalidAction('invalid action for current {} status'.format(state))
            if StateMachine.Severity[current_severity] != StateMachine.NORMAL_SEVERITY_LEVEL:
                return next_state('EXP-1', current_severity, OPEN)

        return next_state('ALL-*', current_severity, current_status)

    @staticmethod
    def is_suppressed(alert):
        return alert.status == BLACKOUT
