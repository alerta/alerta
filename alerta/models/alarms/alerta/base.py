

from flask import current_app

from alerta.models.alarms.base import AlarmModel
from alerta.models.enums import Action, Status
from alerta.models.severity import ALL_OK, Severity, Trend


class Lifecycle(AlarmModel):

    def transition(self, previous_severity: Severity, current_severity: Severity, previous_status: Status=None, current_status: Status=None, **kwargs):
        previous_status = previous_status or Status.OPEN
        current_status = current_status or Status.UNKNOWN
        action = kwargs.get('action', None)  # type: Action

        # transitions driven by operator actions
        if action == Action.ACTION_UNACK:
            return current_severity, Status.OPEN

        if action == Action.ACTION_SHELVE:
            return current_severity, Status.SHELVED

        if action == Action.ACTION_UNSHELVE:
            return current_severity, Status.OPEN

        if action == Action.ACTION_ACK:
            return current_severity, Status.ACK

        if action == Action.ACTION_CLOSE:
            return Severity.from_str(current_app.config['DEFAULT_NORMAL_SEVERITY']), Status.CLOSED

        # transitions driven by alert severity or status changes
        if current_severity in ALL_OK:
            return current_severity, Status.CLOSED

        if current_status in [Status.BLACKOUT, Status.SHELVED]:
            return current_severity, current_status

        if previous_status in [Status.BLACKOUT, Status.CLOSED, Status.EXPIRED]:
            return current_severity, Status.OPEN

        if Severity.trend(previous_severity, current_severity) == Trend.MORE_SEVERE:
            return current_severity, Status.OPEN

        return current_severity, previous_status

    def get_config(self):

        filters = [
            {
                'name': 'All',
                'value': [s.value for s in list(Status)]
            },
            {
                'name': 'Open',
                'value': [Status.OPEN.value, Status.UNKNOWN.value]
            },
            {
                'name': 'Active',
                'value': [Status.OPEN.value, Status.ACK.value, Status.ASSIGN.value]
            },
            {
                'name': 'Shelved',
                'value': [Status.SHELVED.value]
            },
            {
                'name': 'Closed',
                'value': [Status.CLOSED.value, Status.EXPIRED.value]
            },
            {
                'name': 'Blackout',
                'value': [Status.BLACKOUT.value]
            }
        ]

        return {
            'type': current_app.config['ALARM_MODEL'],
            'filters': filters
        }

    def is_suppressed(self, status):
        return status == Status.BLACKOUT
