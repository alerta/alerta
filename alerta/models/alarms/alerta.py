
from alerta.models.alarms import AlarmModel

SEVERITY_MAP = {
    'security': 0,
    'critical': 1,
    'major': 2,
    'minor': 3,
    'warning': 4,
    'normal': 5,
    'ok': 5,
    'cleared': 5,
    'indeterminate': 5,
    'informational': 6,
    'debug': 7,
    'trace': 8,
    'unknown': 9
}
DEFAULT_NORMAL_SEVERITY = 'normal'  # 'normal', 'ok', 'cleared'
DEFAULT_PREVIOUS_SEVERITY = 'indeterminate'
NORMAL_SEVERITY_LEVEL = 5

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
    'text': 'black',
    'highlight': 'skyblue '
}

OPEN = 'open'
ASSIGN = 'assign'
ACK = 'ack'
CLOSED = 'closed'
EXPIRED = 'expired'
BLACKOUT = 'blackout'
SHELVED = 'shelved'
UNKNOWN = 'unknown'
NOT_VALID = 'notValid'


MORE_SEVERE = 'moreSevere'
NO_CHANGE = 'noChange'
LESS_SEVERE = 'lessSevere'


ACTION_ACK = 'ack'
ACTION_UNACK = 'unack'
ACTION_SHELVE = 'shelve'
ACTION_UNSHELVE = 'unshelve'
ACTION_CLOSE = 'close'


class StateMachine(AlarmModel):

    def register(self, app):
        from alerta.management.views import __version__
        self.name = 'Alerta %s' % __version__

        StateMachine.Severity = app.config['SEVERITY_MAP'] or SEVERITY_MAP
        StateMachine.Colors = app.config['COLOR_MAP'] or COLOR_MAP

        StateMachine.DEFAULT_STATUS = UNKNOWN
        StateMachine.DEFAULT_NORMAL_SEVERITY = app.config['DEFAULT_NORMAL_SEVERITY'] or DEFAULT_NORMAL_SEVERITY
        StateMachine.DEFAULT_PREVIOUS_SEVERITY = app.config['DEFAULT_PREVIOUS_SEVERITY'] or DEFAULT_PREVIOUS_SEVERITY

    def trend(self, previous, current):
        assert previous in StateMachine.Severity, "'%s' is not a valid severity" % previous
        assert current in StateMachine.Severity, "'%s' is not a valid severity" % current

        if StateMachine.Severity[previous] > StateMachine.Severity[current]:
            return MORE_SEVERE
        elif StateMachine.Severity[previous] < StateMachine.Severity[current]:
            return LESS_SEVERE
        else:
            return NO_CHANGE

    def transition(self, previous_severity, current_severity, previous_status=None, current_status=None, action=None, **kwargs):
        previous_status = previous_status or OPEN
        current_status = current_status or StateMachine.DEFAULT_STATUS

        assert current_severity in StateMachine.Severity, "'%s' is not a valid severity" % current_severity

        # transitions driven by operator actions
        if action == ACTION_UNACK:
            return current_severity, OPEN
        if action == ACTION_SHELVE:
            return current_severity, SHELVED
        if action == ACTION_UNSHELVE:
            return current_severity, OPEN
        if action == ACTION_ACK:
            return current_severity, ACK
        if action == ACTION_CLOSE:
            return StateMachine.DEFAULT_NORMAL_SEVERITY, CLOSED

        # transitions driven by alert severity or status changes
        if StateMachine.Severity[current_severity] == NORMAL_SEVERITY_LEVEL:
            return current_severity, CLOSED
        if current_status in [BLACKOUT, SHELVED]:
            return current_severity, current_status
        if previous_status in [BLACKOUT, CLOSED, EXPIRED]:
            return current_severity, OPEN
        if self.trend(previous_severity, current_severity) == MORE_SEVERE:
            return current_severity, OPEN

        return current_severity, previous_status

    @staticmethod
    def is_suppressed(alert):
        return alert.status == BLACKOUT
