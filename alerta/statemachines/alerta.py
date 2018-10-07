
from alerta.statemachines import AlarmModel

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
ACTION_RESET = 'reset'
ACTION_UNACK = 'unack'
ACTION_SHELVE = 'shelve'
ACTION_UNSHELVE = 'unshelve'
ACTION_CLOSE = 'close'


class Alerta(AlarmModel):

    Severity = {}  # type: ignore

    DEFAULT_STATUS = UNKNOWN
    DEFAULT_NORMAL_SEVERITY = None

    def __init__(self, app=None):
        self.app = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        Alerta.Severity = app.config['SEVERITY_MAP']
        Alerta.DEFAULT_NORMAL_SEVERITY = app.config['DEFAULT_NORMAL_SEVERITY']

    def trend(self, previous, current):
        if Alerta.Severity[previous] > Alerta.Severity[current]:
            return MORE_SEVERE
        elif Alerta.Severity[previous] < Alerta.Severity[current]:
            return LESS_SEVERE
        else:
            return NO_CHANGE

    def transition(self, previous_severity, current_severity, previous_status=None, current_status=None, action=None):

        previous_status = previous_status or OPEN
        current_status = current_status or UNKNOWN

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
            return Alerta.DEFAULT_NORMAL_SEVERITY, CLOSED

        # transitions driven by alert severity or status changes
        if Alerta.Severity[current_severity] == Alerta.Severity['normal']:
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
